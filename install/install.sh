#!/bin/bash
repo_url="https://github.com/protocolture/extra_freesky"
clone_dir="/opt/chainsky"
launch_script_path="/opt/chainsky/launch/launch_script.sh"



# Step 1: Pull the GitHub repository
#Check dir exists. 
if [ ! -d "$clone_dir" ]; then
    echo "Directory $clone_dir does not exist. Creating it..."
    mkdir -p "$clone_dir"
else
    echo "Directory $clone_dir already exists. Removing."
	rm -d -r "$clone_dir"
	mkdir -p "$clone_dir"
fi

echo "Cloning the repository into $clone_dir..."
git clone $repo_url $clone_dir

chmod +x $launch_script_path
sudo touch /var/log/chainsky_launch.log
sudo chmod 664 /var/log/chainsky_launch.log


# Erroor Checking
if [ $? -ne 0 ]; then
    echo "Error: Failed to clone repository. Please check the URL and your network connection. Exiting."
    exit 1
fi

# Step 2: Set the environment variable with options
echo "Select the mode for Chainsky:"
echo "1) Relay"
echo "2) Reader"
echo "3) Printer"
echo "4) Audio"
read -p "Enter Mode: " choice

case $choice in
    1)
        FREESKY_MODE="DRelay"
        ;;
    2)
        FREESKY_MODE="DReader"
        ;;
    3)
        FREESKY_MODE="DPrinter"
        ;;
    4)
        FREESKY_MODE="DAudio"
        ;;
    *)
        echo "Invalid option. Exiting."
        exit 1
        ;;
esac

# Ensure /etc/chainsky directory exists
if [ ! -d /etc/chainsky ]; then
    mkdir -p /etc/chainsky
    echo "Created /etc/chainsky directory."
fi

# Create the /etc/chainsky/chainsky.conf configuration file with the selected mode
sudo bash -c 'cat <<EOF > /etc/chainsky/chainsky.conf
# /etc/chainsky/chainsky.conf
# Configuration for Freesky

# Mode
FREESKY_MODE='$FREESKY_MODE'

# Directory for Freesky
FREESKY_DIR=/opt/chainsky/freesky
EOF'

echo "Configuration file /etc/chainsky/chainsky.conf "

# Step 3: Set the launch script to run at startup
echo "Setting launch script to run at startup..."

# Create a systemd service file to run the launch script at startup
sudo bash -c 'cat << EOF > /etc/systemd/system/freesky.service
[Unit]
Description=Launch Freesky

[Service]
ExecStart='$launch_script_path'
StandardOutput=journal
StandardError=journal
Restart=always
WorkingDirectory='$HOME/repo'
[Install]
WantedBy=multi-user.target
EOF'

# Enable the systemd service
sudo systemctl enable freesky.service
echo "Installation complete. The extra_freesky script will run at startup."
