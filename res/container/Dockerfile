FROM ubuntu:latest

# Install Java.
ENV echo "DEBIAN_FRONTEND=noninteractive" >> /etc/profile
RUN apt-get update
RUN apt-get install net-tools
RUN apt-get -yq install default-jre
RUN apt-get -yq install openjdk-11-jre-headless
RUN apt-get -yq install openjdk-8-jre-headless
ENV JAVA_HOME /usr/lib/jvm/java-8-oracle

# Install SSH
RUN apt-get update && apt-get install -y openssh-server
RUN mkdir /var/run/sshd
RUN echo 'root:THEPASSWORDYOUCREATED' | chpasswd
RUN sed -i 's/PermitRootLogin prohibit-password/PermitRootLogin yes/' /etc/ssh/sshd_config

# SSH login fix. Otherwise user is kicked off after login
RUN sed 's@session\s*required\s*pam_loginuid.so@session optional pam_loginuid.so@g' -i /etc/pam.d/sshd

ENV NOTVISIBLE "in users profile"
RUN echo "export VISIBLE=now" >> /etc/profile

EXPOSE 22
CMD ["/usr/sbin/sshd", "-D"]