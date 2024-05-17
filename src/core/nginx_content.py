import os

def return_react_nginx_subdomain(sub_domain):
    environ = os.environ.get('APP_ENV', 'qa')
    if environ == "prod":
        return f"""
server {{
    listen 443 ssl;
    server_name {sub_domain};
    ssl_certificate     /etc/nginx/conf.d/ssl/bharat/bundle.crt;
    ssl_certificate_key /etc/nginx/conf.d/ssl/bharat/bharat.key;
    ssl_protocols       TLSv1 TLSv1.1 TLSv1.2 TLSv1.3;
    ssl_ciphers         HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;

    access_log /var/log/nginx/app.log;
    root /var/www/html/react_hrms;
    index index.html index.htm;

    try_files \$uri /index.html;
        location /qxbox/ {{
        rewrite ^/qxbox/(.*)\$ /\$1 break;
        proxy_pass http://unix:/run/gunicorn.sock;
        proxy_set_header Host \$http_host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_set_header X-Forwarded-Port \$server_port;
        proxy_redirect off;
        proxy_read_timeout 300;
        proxy_connect_timeout 300;
        proxy_send_timeout 300;
        send_timeout 300;
    }}

        location /staticfiles/ {{
                root /var/www/html/hrms/public;
        }}
}}

server {{
    listen 80;
    server_name {sub_domain};
    return 301 https://\$host\$request_uri;
}}
"""
    else:
        return f"""
server {{
    listen 80;
    server_name {sub_domain};
    access_log /var/log/nginx/app.log;
    root /var/www/html/react_hrms;
    index index.html index.htm;

    try_files \$uri /index.html;
        location /qxbox/ {{
        rewrite ^/qxbox/(.*)\$ /\$1 break;
        proxy_pass http://unix:/run/gunicorn.sock;
        proxy_set_header Host \$http_host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_set_header X-Forwarded-Port \$server_port;
        proxy_redirect off;
        proxy_read_timeout 300;
        proxy_connect_timeout 300;
        proxy_send_timeout 300;
        send_timeout 300;
    }}

        location /staticfiles/ {{
                root /var/www/html/hrms/public;
        }}
    location / {{
        try_files \$uri \$uri/ = 404;
    }}
}}
"""        

def return_django_nginx_subdomain(sub_domain):
    environ = os.environ.get('APP_ENV', 'qa')
    
    
    if environ == "prod":
        return f"""
server {{
    listen 82;  # Enable SSL on port 82
    server_name {sub_domain};

    # SSL Configuration
    ssl_certificate     /etc/nginx/conf.d/ssl/bharat/bundle.crt;
    ssl_certificate_key /etc/nginx/conf.d/ssl/bharat/bharat.key;
    ssl_protocols       TLSv1 TLSv1.1 TLSv1.2 TLSv1.3;
    ssl_ciphers         HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;

    location = /favicon.ico {{
        access_log off;
        log_not_found off;
    }}

    location /static/ {{
        root /var/www/html/hrms/public;
    }}

    location /media/ {{
        root /var/www/html/hrms/public;
    }}

    location / {{
        include proxy_params;
        proxy_pass http://unix:/run/gunicorn.sock;
        proxy_read_timeout 900;
        proxy_connect_timeout 900;
        proxy_send_timeout 900;
        send_timeout 900;
    }}
}}
"""
    else:
        return f"""
server {{
    listen 82;
    server_name {sub_domain};

    location = /favicon.ico {{ access_log off; log_not_found off; }}
    location /static/ {{
        alias /var/www/html/hrms/public;
    }}
    location /media/ {{
        alias /var/www/html/hrms/public;
    }}


    location / {{
        include proxy_params;
        proxy_pass http://unix:/run/gunicorn.sock;
        proxy_read_timeout 300;
        proxy_connect_timeout 300;
        proxy_send_timeout 300;
        send_timeout 300;
    }}
}}
"""



