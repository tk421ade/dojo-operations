#!/usr/bin/env bash
#
# Debian 12 Installer
#

# configure git and clone repository
apt-get install git nginx virtualenvwrapper -y
cd /opt/
git clone https://github.com/tk421ade/dojo-operations.git
cd /opt/dojo-operations
make prepare

# run gunicorn
# /opt/dojo-operations/venv/bin/gunicorn climate.wsgi

cat > /etc/systemd/system/gunicorn.service << 'EOF'
[Unit]
Description=gunicorn daemon
Requires=gunicorn.socket
After=network.target

[Service]
Type=notify
Environment="DJANGO_SECRET_KEY="
Environment="AWS_ACCESS_KEY_ID="
Environment="AWS_S3_REGION_NAME="
Environment="AWS_SECRET_ACCESS_KEY="
Environment="AWS_STORAGE_BUCKET_NAME="
Environment="TELEGRAM_CHAT_ID="
Environment="TELEGRAM_CHAT_TOKEN="
# the specific user that our service will run as
User=www-data
Group=www-data
# another option for an even more restricted service is
# DynamicUser=yes
# see http://0pointer.net/blog/dynamic-users-with-systemd.html
RuntimeDirectory=gunicorn
WorkingDirectory=/opt/dojo-operations
ExecStart=/opt/dojo-operations/venv/bin/gunicorn shodan.wsgi
ExecReload=/bin/kill -s HUP $MAINPID
KillMode=mixed
TimeoutStopSec=5
PrivateTmp=true

[Install]
WantedBy=multi-user.target
EOF

cat > /etc/systemd/system/gunicorn.socket << 'EOF'
[Unit]
Description=gunicorn socket

[Socket]
ListenStream=/run/gunicorn.sock
# Our service won't need permissions for the socket, since it
# inherits the file descriptor by socket activation
# only the nginx daemon will need access to the socket
SocketUser=www-data
# Optionally restrict the socket permissions even more.
# SocketMode=600

[Install]
WantedBy=sockets.target
EOF

systemctl enable gunicorn.service
systemctl start gunicorn.service

# test that gunicorn over socket is working
# sudo -u www-data curl --unix-socket /run/gunicorn.sock http

# configure nginx
cat > /etc/nginx/sites-available/shodan << 'EOF'


  upstream app_server {
    # fail_timeout=0 means we always retry an upstream even if it failed
    # to return a good HTTP response

    # for UNIX domain socket setups
    server unix:/run/gunicorn.sock fail_timeout=0;

  }

  server {
    listen 80 default_server;
    server_name _;
    return 301 https://$host$request_uri;
  }

  #server {
  #  # if no Host match, close the connection to prevent host spoofing
  #  listen 80 default_server;
  #  return 444;
  #}

  server {
    # use 'listen 80 deferred;' for Linux
    # use 'listen 80 accept_filter=httpready;' for FreeBSD
    #listen 80;
    #listen 80 default_server;
    client_max_body_size 4G;

    listen 443 ssl;
    ssl_certificate /etc/letsencrypt/archive/dojo.brightonkarate.com.au/fullchain1.pem;
    ssl_certificate_key /etc/letsencrypt/archive/dojo.brightonkarate.com.au/privkey1.pem;


    # set the correct host(s) for your site
    #server_name example.com www.example.com;

    keepalive_timeout 5;

    # path for static files
    root /var/www/html;

    location / {
      # checks for static file, if not found proxy to app
      try_files $uri @proxy_to_app;
    }

    location @proxy_to_app {
      proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
      proxy_set_header X-Forwarded-Proto $scheme;
      proxy_set_header Host $http_host;
      # we don't want nginx trying to do something clever with
      # redirects, we set the Host: header above already.
      proxy_redirect off;
      proxy_pass http://app_server;
    }

    error_page 500 502 503 504 /500.html;
    location = /500.html {
      root /path/to/app/current/public;
    }
    location /static/ {
      root /var/www/;
    }

  }
EOF

rm -f /etc/nginx/sites-enabled/default
ln -s /etc/nginx/sites-available/shodan /etc/nginx/sites-enabled/shodan
mkdir -p /var/www/static
cd /opt/dojo-operations

systemctl enable nginx.service
systemctl start nginx.service

/sbin/iptables -I INPUT -p tcp -m tcp --dport 80 -j ACCEPT
/sbin/iptables -I INPUT -p tcp -m tcp --dport 443 -j ACCEPT

# install database
apt-get install postgresql -y
su - postgres -c "createdb shodan"

cat > /etc/postgresql/15/main/pg_hba.conf << 'EOF'
local   all             postgres                                peer
local   all             all                                     peer
host    all             all             127.0.0.1/32            trust
host    all             all             ::1/128                 scram-sha-256
local   replication     all                                     peer
host    replication     all             127.0.0.1/32            scram-sha-256
host    replication     all             ::1/128                 scram-sha-256
EOF

systemctl restart postgresql
cd /opt/dojo-operations
make collectstatic

# install SSL
# apt-get install certbot python3-certbot-nginx -y
# certbot certonly --nginx
#
# Renew
# certbot renew --dry-run
#
# nginx redirect to https
# server {
#    listen 80 default_server;
#
#    server_name _;
#
#    return 301 https://$host$request_uri;
#}
#
