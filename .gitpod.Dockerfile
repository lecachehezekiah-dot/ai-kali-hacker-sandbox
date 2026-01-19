FROM kalilinux/kali-rolling
RUN apt update && apt install -y python3-pip curl wget sudo openssh-server kali-linux-headless
RUN useradd -m -s /bin/bash kali && echo "kali:kali" | chpasswd && adduser kali sudo
USER kali
WORKDIR /workspace
