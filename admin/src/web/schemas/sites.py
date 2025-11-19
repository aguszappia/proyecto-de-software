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
    is_favorite = fields.Bool(dump_default=False)
    visits = fields.Int()
    average_rating = fields.Float(allow_none=True)
    total_reviews = fields.Int(allow_none=True)
    images = fields.Method("get_images")

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

    def get_images(self, obj):
        images = self._get_value(obj, "images") or []
        serialized = []
        for entry in images:
            if entry is None:
                continue
            if isinstance(entry, dict):
                url = entry.get("src") or entry.get("url") or entry.get("image_url")
                if not url:
                    continue
                title = entry.get("title") or entry.get("alt")
                serialized.append(
                    {
                        "id": entry.get("id"),
                        "url": url,
                        "src": url,
                        "title": title,
                        "alt": entry.get("alt") or title,
                        "description": entry.get("description"),
                        "order_index": entry.get("order_index"),
                        "is_cover": entry.get("is_cover", False),
                    },
                )
                continue
            url = getattr(entry, "url", None)
            if not url:
                continue
            title = getattr(entry, "title", None)
            serialized.append(
                {
                    "id": getattr(entry, "id", None),
                    "url": url,
                    "src": url,
                    "title": title,
                    "alt": title,
                    "description": getattr(entry, "description", None),
                    "order_index": getattr(entry, "order_index", None),
                    "is_cover": getattr(entry, "is_cover", False),
                },
            )
        return serialized


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


class ReviewSchema(Schema):
    id = fields.Int()
    site_id = fields.Int()
    user_id = fields.Int()
    rating = fields.Int()
    comment = fields.Str()
    status = fields.Str()
    rejection_reason = fields.Str(allow_none=True)
    created_at = fields.Method("get_created_at")
    updated_at = fields.Method("get_updated_at")
    author_name = fields.Str(load_default=None)

    def _format_datetime(self, value):
        if value is None:
            return None
        if isinstance(value, str):
            return value
        return value.isoformat()

    def get_created_at(self, obj):
        value = getattr(obj, "created_at", None)
        return self._format_datetime(value)

    def get_updated_at(self, obj):
        value = getattr(obj, "updated_at", None)
        return self._format_datetime(value)


review_schema = ReviewSchema()
review_list_schema = ReviewSchema(many=True)
