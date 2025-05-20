# Step 1: Use a pre-built Android emulator image as the base
ARG EMULATOR_IMAGE_TAG=us-docker.pkg.dev/android-emulator-268719/images/30-google-x64:30.1.2
FROM ${EMULATOR_IMAGE_TAG}

# Switch to root for installations
USER root

# Step 2: Install Python 3 and pip
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        python3 \
        python3-pip \
        python3-venv \
    && rm -rf /var/lib/apt/lists/*

# Step 3: Create a working directory for your AI agent inside the image
# Let's use /opt/navi_agent for clarity
WORKDIR /opt/navi_agent

# Step 4: Copy your ENTIRE project content (from the build context root)
# into the working directory inside the image.
# This will copy 'scripts/', 'apps/', 'learn.py', 'config.yaml', 'requirements.txt', etc.
# into /opt/navi_agent/
COPY . /opt/navi_agent/

# Step 5: Install Python dependencies for your agent
# requirements.txt is now at /opt/navi_agent/requirements.txt
RUN python3 -m pip install --no-cache-dir -r requirements.txt

# The base image (FROM ${EMULATOR_IMAGE_TAG}) already has an ENTRYPOINT
# defined (usually /android-entrypoint.sh) which starts the emulator and ADB.
# We will later create a custom wrapper script.

# Add a simple healthcheck for ADB
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s \
  CMD adb devices | grep -q "emulator-5554" || exit 1

# Expose ports (already done by base image, but good for clarity)
EXPOSE 5555
EXPOSE 8554

# The CMD of the base image is usually empty or passes args to the entrypoint.
# We don't override it yet.
# When this image runs, the base emulator image's entrypoint will start the emulator.
# Your project files will be at /opt/navi_agent/
# You can later exec into the container to run:
# python3 /opt/navi_agent/learn.py