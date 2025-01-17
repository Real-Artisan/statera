set -e

docker build -t statera-api:latest --platform=linux/amd64 .

docker tag statera-api:latest realartisan/statera:latest

docker push realartisan/statera:latest

echo "Image pushed to Docker Hub"