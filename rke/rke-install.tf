locals {
  os_password = data.vault_generic_secret.os.data["password"]
  os_username = data.vault_generic_secret.os.data["username"]
  subscr_user = data.vault_generic_secret.os.data["subscr-user"]
  subscr_pw = data.vault_generic_secret.os.data["subscr-pw"]
}

resource "null_resource" "rke2_install" {
  # Trigger this whenever the server is provisioned by Intersight
  # Replace 'intersight_server_ip' with your actual resource output
  connection {
    type     = "ssh"
    user     = local.os_username # Or your cloud-init user
    password = local.os_password
    host     = "172.16.115.41"
    timeout      = "15m"
  }

  provisioner "remote-exec" {
    inline = [
      # 1. Register Red Hat Subscription
      "subscription-manager unregister || true",
      "subscription-manager clean || true",
      "subscription-manager register --username '${local.subscr_user}' --password '${local.subscr_pw}' --auto-attach --force",
      
      # 2. Prepare RHEL 8.9 for RKE2 (Enable necessary repos)
      "yum update -y",
      "systemctl stop firewalld && systemctl disable firewalld", # RKE2 manages its own networking

      # 2. Enable the EXACT repos needed for container-selinux
      "subscription-manager repos --enable=rhel-9-for-x86_64-baseos-rpms --enable=rhel-9-for-x86_64-appstream-rpms --enable=codeready-builder-for-rhel-9-x86_64-rpms",
      
      # 3. CRITICAL: Clear all dnf/yum metadata to force a fresh look at the new repos
      "dnf clean all",
      "dnf makecache",
      "dnf install -y container-selinux",

      # 3. Install RKE2 using the official script
      "curl -sfL https://get.rke2.io | sh -",

      # 4. Create RKE2 Config (Replace token and server-ip as needed)
      "mkdir -p /etc/rancher/rke2",
      "echo 'token: '${local.os_password}'' > /etc/rancher/rke2/config.yaml",
      "echo 'write-kubeconfig-mode: \"0644\"' >> /etc/rancher/rke2/config.yaml",

      # 5. Enable and Start RKE2
      "systemctl enable rke2-server.service",
      "systemctl start rke2-server.service",
      "export KUBECONFIG=/etc/rancher/rke2/rke2.yaml",
      "echo 'export KUBECONFIG=/etc/rancher/rke2/rke2.yaml' >> ~/.bashrc",
      "export KUBECONFIG=/etc/rancher/rke2/rke2.yaml",
      "echo 'export KUBECONFIG=/etc/rancher/rke2/rke2.yaml' >> ~/.bashrc",
      "echo 'export PATH=$PATH:/var/lib/rancher/rke2/bin' >> ~/.bashrc",
      "source ~/.bashrc"

    ]
  }
}