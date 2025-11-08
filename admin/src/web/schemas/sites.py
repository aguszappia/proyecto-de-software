from marshmallow import Schema, fields

class SiteSchema(Schema): # revisar si faltan mas campos
    title = fields.Str()
    short_description = fields.Str()  
    long_description = fields.Str()
    lat = fields.Float()
    lon = fields.Float()

site_shema = SiteSchema(many=True)