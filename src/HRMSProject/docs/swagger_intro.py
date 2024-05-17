DESCRIPTION = """
# Introduction

The API is organized around [REST](https://en.wikipedia.org/wiki/Representational_state_transfer) principle.
Our API has human-friendly URL endpoints, accepts and returns [JSON](https://en.wikipedia.org/wiki/JSON) data, uses
standard [HTTP status codes](https://en.wikipedia.org/wiki/List_of_HTTP_status_codes) and outputs useful error
messages.

# Access Tokens

Authentication to the API is performed via
[HTTP Basic Authentication](https://en.wikipedia.org/wiki/Basic_access_authentication).
All of our endpoints, except those which are a part of `auth-service`, require an access token in the form of
[JWT](https://jwt.io). When a token expires you will need to obtain a new one. A token can be obtained
[here](#operation/auth-service_tokens_create). Once obtained, you can include it in the `Authorization` header of an
HTTP request as follows:
```
{{
    Authorization: "Bearer <access_token>"
}}
```

All API requests must be made over [HTTPS](https://en.wikipedia.org/wiki/HTTPS). Calls made over plain HTTP will fail.

# Errors

We use HTTP response codes that are standard and hence intuitive. All error codes can be looked up
[here](https://en.wikipedia.org/wiki/List_of_HTTP_status_codes#4xx_Client_errors). HTTP response codes resulting in
`4xx` indicate an error that failed given the information provided. All `4xx` errors are shown with a brief explanation
of the error.

`5xx` HTTP response codes mean that our servers have encountered an error and we will be automatically notified and fix
it as soon as possible.

# Filtering

Almost all endpoints can be filtered against certain fields. These fields can also be combined together. In order to
filter you need to provide fields and their values as standard URL query parameters, e.g. `?color=Red&type=Large`. For a
list of all available filters please see a documentation section of a particular endpoint.

# Pagination

```Available Soon```

# Performance

To reduce the size of a response when retrieving data from an endpoint make sure to include either the `fields` or
`omit` URL query parameter.
* Specifying `fields` will return only certain fields per item, e.g. `?fields=self,color,type`;
* Specifying `omit` will omit certain fields per item, e.g. `?omit=createdAt,updatedAt`.

# HATEOAS

Almost all endpoints come with [HATEOAS](https://en.wikipedia.org/wiki/HATEOAS) links in the following format:
```
links: [
  {{
    rel: "departments",
    href: "https://example.com/api/policies/"
  }},
  ...
]
```

These links contain related resources and are useful for navigating through them without looking them in the
documentation.
"""
