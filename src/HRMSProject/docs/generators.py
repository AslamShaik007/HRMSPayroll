from drf_yasg.generators import OpenAPISchemaGenerator as _OpenAPISchemaGenerator


class OpenAPISchemaGenerator(_OpenAPISchemaGenerator):
    """This class iterates over all registered API endpoints and returns
    an appropriate OpenAPI 3.0 compliant schema.

    AJAY, 11.01.2023
    """

    def get_schema(self, request=None, public=False):
        return super().get_schema(request, public)
