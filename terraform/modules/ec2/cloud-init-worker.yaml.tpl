#cloud-config
runcmd:
  - apt-get update && apt-get install -y apt-transport-https ca-certificates curl gpg containerd
  - mkdir -p /etc/containerd && containerd config default | tee /etc/containerd/config.toml
  - sed -i 's/SystemdCgroup = false/SystemdCgroup = true/' /etc/containerd/config.toml
  - systemctl restart containerd
  - mkdir -p /etc/apt/keyrings
  - curl -fsSL https://pkgs.k8s.io/core:/stable:/v1.30/deb/Release.key | gpg --dearmor -o /etc/apt/keyrings/kubernetes-apt-keyring.gpg
  - echo 'deb [signed-by=/etc/apt/keyrings/kubernetes-apt-keyring.gpg] https://pkgs.k8s.io/core:/stable:/v1.30/deb/ /' | tee /etc/apt/sources.list.d/kubernetes.list
  - apt-get update && apt-get install -y kubelet kubeadm && apt-mark hold kubelet kubeadm
  - until nc -z ${control_plane_private_ip} 6443; do sleep 10; done
  - kubeadm join ${control_plane_private_ip}:6443 --token=${kubeadm_token} --discovery-token-unsafe-skip-ca-verification
