import reversion
import simplejson

from django.utils.translation import get_language
from django.core import serializers
from django.contrib.admin.utils import unquote, quote
from django.core.exceptions import PermissionDenied
from django.core.urlresolvers import reverse


class TranslatableVersionAdmin(reversion.VersionAdmin):
    change_form_template = "mptt_publisher/hvad/trans_change_form.html"
    object_history_template = "reversion/trans_recover_form.html"

    def history_view(self, request, object_id, extra_context=None):
        if not self.has_change_permission(request):
            raise PermissionDenied
        object_id = unquote(object_id)
        active_lang = request.GET.get('language') or get_language()
        opts = self.model._meta
        action_list = [
            {
                "revision": version.revision,
                "url": reverse("%s:%s_%s_revision" % (
                    self.admin_site.name, opts.app_label, opts.model_name),
                    args=(quote(version.object_id), version.id)),
            }
            for version in self._order_version_queryset(
                self.revision_manager.get_for_object_reference(
                    self.model,
                    object_id,
                ).select_related("revision__user"))
            if simplejson.loads(version.serialized_data)[0]['fields'].get(
                'language_code'
            ) == active_lang
        ]
        context = {"action_list": action_list}
        context.update(extra_context or {})
        return super().history_view(request, object_id, context)

    def save_model(self, request, obj, form, change):
        if not hasattr(self, 'model'):
            raise AttributeError("You need to specify 'model', attr")

        serialized = serializers.serialize(
            'json',
            [obj.translations.get(
                language_code=request.GET.get('language') or get_language()
            )]
        )
        try:
            revision = reversion.get_for_object_reference(
                self.model, obj.pk)[0]
            revision.serialized_data = serialized
            revision.save()
        except IndexError:
            pass
        return super().save_model(request, obj, form, change)
