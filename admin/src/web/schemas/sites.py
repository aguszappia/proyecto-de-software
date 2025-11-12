from marshmallow import Schema, fields, validate


class SiteSchema(Schema):
    id = fields.Int()
    name = fields.Str()
    short_description = fields.Str()
    description = fields.Str(attribute="full_description")
    city = fields.Str()
    province = fields.Str()
    country = fields.Method("get_country")
    lat = fields.Float(attribute="latitude")
    long = fields.Float(attribute="longitude")
    tags = fields.Method("get_tags")
    state_of_conservation = fields.Method("get_state_of_conservation")
    category = fields.Method("get_category")
    inaguration_year = fields.Int(allow_none=True)
    inserted_at = fields.Method("get_inserted_at")
    updated_at = fields.Method("get_updated_at")
    cover_image_url = fields.Method("get_cover_image_url")
    cover_image_title = fields.Method("get_cover_image_title")

    def _get_value(self, obj, attr, default=None):
        if isinstance(obj, dict):
            return obj.get(attr, default)
        return getattr(obj, attr, default)

    def get_country(self, obj):
        value = self._get_value(obj, "country")
        return value or "AR"

    def get_tags(self, obj):
        tags = self._get_value(obj, "tags") or []
        if tags and not isinstance(tags[0], str):
            normalized = [
                getattr(tag, "slug", getattr(tag, "name", "")).strip()
                for tag in tags
            ]
            return [tag for tag in normalized if tag]
        return tags

    def get_state_of_conservation(self, obj):
        value = self._get_value(obj, "conservation_status")
        if hasattr(value, "value"):
            return value.value
        return value

    def get_category(self, obj):
        value = self._get_value(obj, "category")
        if hasattr(value, "value"):
            return value.value
        return value

    def _format_datetime(self, value):
        if value is None:
            return None
        if isinstance(value, str):
            return value
        return value.isoformat()

    def get_inserted_at(self, obj):
        value = self._get_value(obj, "created_at")
        return self._format_datetime(value)

    def get_updated_at(self, obj):
        value = self._get_value(obj, "updated_at")
        return self._format_datetime(value)

    def get_cover_image_url(self, obj):
        return self._get_value(obj, "cover_image_url")

    def get_cover_image_title(self, obj):
        return self._get_value(obj, "cover_image_title")


site_schema = SiteSchema(many=True)
single_site_schema = SiteSchema()


class SiteCreateSchema(Schema):
    name = fields.Str(required=True, validate=validate.Length(min=1))
    short_description = fields.Str(required=True, validate=validate.Length(min=1))
    description = fields.Str(required=True, validate=validate.Length(min=1))
    city = fields.Str(required=True, validate=validate.Length(min=1))
    province = fields.Str(required=True, validate=validate.Length(min=1))
    country = fields.Str(load_default=None)
    lat = fields.Float(required=True)
    long = fields.Float(required=True)
    state_of_conservation = fields.Str(required=True, validate=validate.Length(min=1))
    category = fields.Str(required=True, validate=validate.Length(min=1))
    inaguration_year = fields.Int(allow_none=True)
    tags = fields.Raw(load_default=list)


site_create_schema = SiteCreateSchema()
