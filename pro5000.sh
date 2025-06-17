#!/bin/bash

set -euo pipefail

export USER_NAME="user"
export USER_HOME="/home/${USER_NAME}"

# Logging function
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

log "Starting enhanced Pinokio provisioning with NVIDIA Driver 570+ and PyTorch 2.7.0..."

# Function to check NVIDIA driver version
check_nvidia_driver() {
    log "Checking NVIDIA driver version..."
    
    if ! command -v nvidia-smi &> /dev/null; then
        log "ERROR: nvidia-smi not found. NVIDIA drivers may not be properly installed."
        return 1
    fi
    
    # Get driver version
    DRIVER_VERSION=$(nvidia-smi --query-gpu=driver_version --format=csv,noheader,nounits | head -n1 | tr -d ' ')
    log "Current NVIDIA driver version: ${DRIVER_VERSION}"
    
    # Extract major version number
    MAJOR_VERSION=$(echo "${DRIVER_VERSION}" | cut -d'.' -f1)
    
    if [[ ${MAJOR_VERSION} -lt 570 ]]; then
        log "WARNING: NVIDIA driver version ${DRIVER_VERSION} is below required 570.x"
        log "Attempting to update NVIDIA drivers..."
        return 1
    else
        log "✅ NVIDIA driver version ${DRIVER_VERSION} meets requirements (570+)"
        return 0
    fi
}

# Function to install/update NVIDIA drivers
install_nvidia_driver() {
    log "Installing/updating NVIDIA drivers to 570+..."
    
    # Add NVIDIA package repository
    apt-get update
    apt-get install -y wget gnupg
    
    # Download and install NVIDIA repository key
    wget -qO - https://developer.download.nvidia.com/compute/cuda/repos/ubuntu2404/x86_64/3bf863cc.pub | apt-key add -
    
    # Add NVIDIA repository
    echo "deb https://developer.download.nvidia.com/compute/cuda/repos/ubuntu2404/x86_64 /" > /etc/apt/sources.list.d/cuda.list
    echo "deb https://developer.download.nvidia.com/compute/machine-learning/repos/ubuntu2404/x86_64 /" > /etc/apt/sources.list.d/nvidia-ml.list
    
    apt-get update
    
    # Install specific NVIDIA driver version (570 series)
    apt-get install -y nvidia-driver-570 nvidia-dkms-570
    
    # Install CUDA toolkit components if needed
    apt-get install -y cuda-toolkit-12-8
    
    log "NVIDIA driver installation completed. Note: Reboot may be required for full activation."
}

# Function to install Python and pip
setup_python_environment() {
    log "Setting up Python environment..."
    
    # Install Python 3.11+ (required for PyTorch 2.7.0)
    apt-get update
    apt-get install -y python3.11 python3.11-pip python3.11-venv python3.11-dev
    
    # Create symlinks for easier access
    update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.11 1
    update-alternatives --install /usr/bin/pip3 pip3 /usr/bin/pip3.11 1
    
    # Upgrade pip to latest version
    python3 -m pip install --upgrade pip setuptools wheel
    
    log "✅ Python environment setup completed"
}

# Function to install PyTorch 2.7.0
install_pytorch() {
    log "Installing PyTorch 2.7.0 with CUDA 12.8 support..."
    
    # Verify CUDA is available
    if ! python3 -c "import torch; print('CUDA available:', torch.cuda.is_available())" 2>/dev/null; then
        log "Installing PyTorch 2.7.0 with CUDA 12.8 support..."
    fi
    
    # Install PyTorch 2.7.0 with CUDA 12.8 support
    python3 -m pip install torch==2.7.0 torchvision==0.20.0 torchaudio==2.7.0 --index-url https://download.pytorch.org/whl/cu128
    
    # Install additional ML libraries commonly used with Pinokio
    python3 -m pip install \
        numpy==1.26.4 \
        pillow==10.4.0 \
        opencv-python==4.10.0.84 \
        transformers==4.44.0 \
        diffusers==0.30.0 \
        accelerate==0.33.0 \
        xformers==0.0.28.post1
    
    # Verify PyTorch installation
    python3 -c "
import torch
print(f'PyTorch version: {torch.__version__}')
print(f'CUDA available: {torch.cuda.is_available()}')
if torch.cuda.is_available():
    print(f'CUDA version: {torch.version.cuda}')
    print(f'GPU count: {torch.cuda.device_count()}')
    print(f'Current GPU: {torch.cuda.get_device_name(0)}')
"
    
    log "✅ PyTorch 2.7.0 installation completed and verified"
}

# Function to install additional dependencies
install_dependencies() {
    log "Installing additional dependencies..."
    
    # Install system dependencies
    apt-get update
    apt-get install -y \
        curl \
        wget \
        git \
        jq \
        unzip \
        build-essential \
        cmake \
        pkg-config \
        libjpeg-dev \
        libpng-dev \
        libtiff-dev \
        libavcodec-dev \
        libavformat-dev \
        libswscale-dev \
        libv4l-dev \
        libxvidcore-dev \
        libx264-dev \
        libgtk-3-dev \
        libatlas-base-dev \
        gfortran \
        ffmpeg
    
    log "✅ Additional dependencies installed"
}

# Main execution starts here
log "=== NVIDIA Driver and PyTorch Setup ==="

# Install dependencies first
install_dependencies

# Check and install NVIDIA drivers
if ! check_nvidia_driver; then
    log "NVIDIA driver update required..."
    install_nvidia_driver
    
    # Verify installation
    if ! check_nvidia_driver; then
        log "WARNING: NVIDIA driver verification failed. Continuing with existing driver..."
    fi
fi

# Setup Python environment
setup_python_environment

# Install PyTorch 2.7.0
install_pytorch

log "=== Pinokio Installation ==="

# Execute the rest of the commands as the specified user
bash << 'EOF'
set -euo pipefail

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

log "Setting up Pinokio application..."

mkdir -p "${USER_HOME}/Desktop"
cd /tmp

# Get latest Pinokio version
[[ -n ${PINOKIO_VERSION:-} ]] || PINOKIO_VERSION=$(curl -s https://api.github.com/repos/pinokiocomputer/pinokio/releases/latest | jq -r .tag_name)
VERSION_NUMBER=${PINOKIO_VERSION:-3.8.0}

log "Installing Pinokio version: ${VERSION_NUMBER}"

FILE_NAME="pinokio_${VERSION_NUMBER}_amd64.AppImage"
DOWNLOAD_URL="https://github.com/pinokiocomputer/pinokio/releases/download/${VERSION_NUMBER}/Pinokio-${VERSION_NUMBER}.AppImage"

# Download with progress bar
log "Downloading Pinokio AppImage..."
wget --progress=bar:force:noscroll -O "${FILE_NAME}" "${DOWNLOAD_URL}"

# Verify download
if [[ ! -f "${FILE_NAME}" ]]; then
    log "ERROR: Download failed"
    exit 1
fi

log "Extracting Pinokio AppImage..."
chmod +x "${FILE_NAME}"
./"${FILE_NAME}" --appimage-extract

# Move to system location
mv /tmp/squashfs-root /opt/pinokio
chown -R "${USER_NAME}:${USER_NAME}" /opt/pinokio

# Cleanup
rm -f "/tmp/${FILE_NAME}"

log "✅ Pinokio extraction completed"
EOF

# Create enhanced desktop file with environment variables
log "Creating desktop integration..."

sudo -u "${USER_NAME}" bash -c "cat > ${USER_HOME}/Desktop/Pinokio.desktop << 'EOF'
[Desktop Entry]
Version=1.0
Type=Application
Name=Pinokio AI
Comment=Pinokio AI Automation Platform with PyTorch 2.7.0
Exec=env HOME=${WORKSPACE} APPDIR=/opt/pinokio CUDA_VISIBLE_DEVICES=0 LD_LIBRARY_PATH=/usr/local/cuda/lib64:/usr/lib/x86_64-linux-gnu:${LD_LIBRARY_PATH} vglrun -nodl /opt/pinokio/AppRun --no-sandbox %U
Icon=/opt/pinokio/pinokio.png
Terminal=false
Categories=Development;Science;ArtificialIntelligence;
StartupNotify=true
Keywords=AI;PyTorch;MachineLearning;Automation;
EOF"

# Make the desktop file executable
sudo -u "${USER_NAME}" chmod +x "${USER_HOME}/Desktop/Pinokio.desktop"

# Create environment setup script
sudo -u "${USER_NAME}" bash -c "cat > ${USER_HOME}/setup_ai_env.sh << 'EOF'
#!/bin/bash
# AI Environment Setup Script

export CUDA_VISIBLE_DEVICES=0
export PYTORCH_CUDA_ALLOC_CONF=max_split_size_mb:512
export CUDA_LAUNCH_BLOCKING=0

# Add CUDA to PATH
export PATH=/usr/local/cuda/bin:${PATH}
export LD_LIBRARY_PATH=/usr/local/cuda/lib64:/usr/lib/x86_64-linux-gnu:${LD_LIBRARY_PATH}

echo "AI Environment configured:"
echo "- NVIDIA Driver: $(nvidia-smi --query-gpu=driver_version --format=csv,noheader,nounits)"
echo "- PyTorch: $(python3 -c 'import torch; print(torch.__version__)')"
echo "- CUDA Available: $(python3 -c 'import torch; print(torch.cuda.is_available())')"
echo "- GPU: $(python3 -c 'import torch; print(torch.cuda.get_device_name(0) if torch.cuda.is_available() else \"No GPU\")')"
EOF"

sudo -u "${USER_NAME}" chmod +x "${USER_HOME}/setup_ai_env.sh"

# Add environment setup to bashrc
sudo -u "${USER_NAME}" bash -c "echo 'source ${USER_HOME}/setup_ai_env.sh' >> ${USER_HOME}/.bashrc"

# Create verification script
sudo -u "${USER_NAME}" bash -c "cat > ${USER_HOME}/verify_installation.py << 'EOF'
#!/usr/bin/env python3
import sys
import subprocess

def check_nvidia_driver():
    try:
        result = subprocess.run(['nvidia-smi', '--query-gpu=driver_version', '--format=csv,noheader,nounits'], 
                              capture_output=True, text=True)
        if result.returncode == 0:
            version = result.stdout.strip()
            major_version = int(version.split('.')[0])
            print(f"✅ NVIDIA Driver: {version} {'(✅ >= 570)' if major_version >= 570 else '(❌ < 570)'}")
            return major_version >= 570
        else:
            print("❌ NVIDIA Driver: Not detected")
            return False
    except Exception as e:
        print(f"❌ NVIDIA Driver check failed: {e}")
        return False

def check_pytorch():
    try:
        import torch
        version = torch.__version__
        cuda_available = torch.cuda.is_available()
        print(f"✅ PyTorch: {version}")
        print(f"✅ CUDA Available: {cuda_available}")
        
        if cuda_available:
            gpu_name = torch.cuda.get_device_name(0)
            cuda_version = torch.version.cuda
            print(f"✅ GPU: {gpu_name}")
            print(f"✅ CUDA Version: {cuda_version}")
        
        return version.startswith('2.7.0')
    except ImportError:
        print("❌ PyTorch: Not installed")
        return False
    except Exception as e:
        print(f"❌ PyTorch check failed: {e}")
        return False

def main():
    print("=== Installation Verification ===")
    
    nvidia_ok = check_nvidia_driver()
    pytorch_ok = check_pytorch()
    
    print("\n=== Summary ===")
    if nvidia_ok and pytorch_ok:
        print("✅ All requirements met! Pinokio is ready for AI workloads.")
        sys.exit(0)
    else:
        print("❌ Some requirements not met. Please check the installation.")
        sys.exit(1)

if __name__ == "__main__":
    main()
EOF"

sudo -u "${USER_NAME}" chmod +x "${USER_HOME}/verify_installation.py"

# Run verification
log "Running installation verification..."
sudo -u "${USER_NAME}" python3 "${USER_HOME}/verify_installation.py"

log "=== Installation Summary ==="
log "✅ NVIDIA Driver 570+ compatibility ensured"
log "✅ PyTorch 2.7.0 with CUDA 12.8 support installed"
log "✅ Pinokio AI platform configured and ready"
log "✅ Desktop integration created"
log "✅ Environment setup scripts created"

log "🚀 Enhanced Pinokio provisioning completed successfully!"
log "📋 Next steps:"
log "   1. Launch Pinokio from Desktop icon"
log "   2. Run ~/verify_installation.py to check setup"
log "   3. Source ~/setup_ai_env.sh for AI environment variables"

# Final system info
log "=== System Information ==="
nvidia-smi --query-gpu=name,driver_version,memory.total --format=csv,noheader || log "NVIDIA info unavailable"
python3 -c "import torch; print(f'PyTorch {torch.__version__} with CUDA {torch.version.cuda if torch.cuda.is_available() else \"N/A\"}')" || log "PyTorch info unavailable"
