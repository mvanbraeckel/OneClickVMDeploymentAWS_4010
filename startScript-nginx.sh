#!/bin/bash

# nginx some-content-nginx start script
# For container: image nginx, which creates image and container some-content-nginx
# Visit URL: {public-ipv4-address}:8080/ to see index.html

cat > Dockerfile << EOF
FROM nginx
COPY static-html-directory /usr/share/nginx/html
EOF

mkdir static-html-directory
cd static-html-directory

touch index.html
cat > index.html << EOF
<!DOCTYPE html>
<html>
    <head>
        <!-- head definitions go here -->
    </head>
    <body>
        <h1>CIS*4010 Cloud Computing - A2: nginx | It works!</h1>
    </body>
</html>
EOF

chmod 666 index.html

cd ..

sudo docker build -t some-content-nginx .
sudo docker run --name some-nginx -d -p 8080:80 some-content-nginx
