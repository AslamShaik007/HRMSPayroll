def get_domain(env):
    if env == "qa":
        return "indianpayrollservice.com".split(".")
    if env == "prod":
        return "bharatpayroll.com".split(".")
    return None, None
