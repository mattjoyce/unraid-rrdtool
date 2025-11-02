# Stop and remove the container
docker stop rrdtool-graphs
docker rm rrdtool-graphs

# Recreate with correct mounts
docker run -d \
  --name rrdtool-graphs \
  --restart unless-stopped \
  -e TZ=Australia/Sydney \
  -e PYTHONPATH=/scripts \
  -p 8080:8080 \
  -v /mnt/user/appdata/rrdtool-graphs/config:/config:rw \
  -v /mnt/user/appdata/rrdtool-graphs/data:/data:rw \
  -v /sys:/hostsys:ro \
  -v /var/local/emhttp:/var/local/emhttp:ro \
  rrdtool-graphs:latest


