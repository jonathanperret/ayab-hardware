#!/bin/bash
# setup-kicad.sh [--start-docker]  -- prepare a fresh (Ubuntu 24.04, root) cloud container for the board
# tooling in scripts/kicad and ayab-sr-esp32/{tools,enclosure/tools}:
#   - Docker (preinstalled in Claude Code cloud images; the daemon is not running: started here, it has
#     no systemd and may die now and then -- scripts/kicad/kicad.sh restarts it with --start-docker)
#   - KiCad 10.0.7 as Docker images from mirror.gcr.io (Docker Hub rate-limits anonymous pulls):
#     kicad/kicad:10.0.7 (kicad-cli + pcbnew Python) and kicad/kicad:10.0.7-full (3D models, for renders
#     and STL/GLB exports). KiCad is not installed natively: the 10.x PPA is not needed.
#   - Freerouting 2.5.0 (Maven Central jar, sha1-checked) and Java 25 to run it (class files need 25)
#   - OpenSCAD + xvfb (headless OpenGL previews), ffmpeg, rsvg-convert, zip, python3 numpy + pillow
# Network: needs apt mirrors, mirror.gcr.io, repo1.maven.org (and jlcpcb.com for scripts/kicad/jlc).
# --start-docker only (re)starts the Docker daemon.
set -e
start_docker() {
  docker info >/dev/null 2>&1 && return 0
  command -v dockerd >/dev/null || { apt-get install -y -q docker.io >/dev/null; }
  echo "starting dockerd" >&2
  (nohup dockerd > /tmp/dockerd.log 2>&1 &)
  for i in $(seq 180); do docker info >/dev/null 2>&1 && return 0; sleep 1; done
  echo "dockerd did not start, see /tmp/dockerd.log" >&2; return 1
}
[ "$1" = "--start-docker" ] && { start_docker; exit $?; }

export DEBIAN_FRONTEND=noninteractive
apt-get update -q >/dev/null
apt-get install -y -q --no-install-recommends openjdk-25-jre-headless openscad xvfb ffmpeg librsvg2-bin zip \
  python3-numpy python3-pil >/dev/null
start_docker
for img in mirror.gcr.io/kicad/kicad:10.0.7 mirror.gcr.io/kicad/kicad:10.0.7-full; do
  docker image inspect "$img" >/dev/null 2>&1 || docker pull -q "$img"
done

JAR_DIR=$HOME/.cache/kicad-tools; JAR=$JAR_DIR/freerouting-2.5.0.jar
URL=https://repo1.maven.org/maven2/app/freerouting/freerouting/2.5.0/freerouting-2.5.0-executable.jar
mkdir -p "$JAR_DIR"
if [ ! -s "$JAR" ]; then
  curl -sSfL -o "$JAR.tmp" "$URL"
  [ "$(sha1sum < "$JAR.tmp" | cut -d' ' -f1)" = "$(curl -sSfL "$URL.sha1")" ] || { echo "freerouting sha1 mismatch" >&2; exit 1; }
  mv "$JAR.tmp" "$JAR"
fi

echo "kicad-cli $(docker run --rm mirror.gcr.io/kicad/kicad:10.0.7 kicad-cli version 2>/dev/null)"
echo "freerouting $JAR"
echo "openscad $(openscad --version 2>&1 | head -1)"
