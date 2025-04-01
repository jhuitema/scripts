# .bashrc

if [ -f ~/.kube/config ]; then
    export KUBECONFIG=~/.kube/config
fi

# User specific aliases and functions
alias setns="kubectl config set-context --current --namespace $1"
alias getns="kubectl config get-contexts"
alias kd="kubectl drain --force --ignore-daemonsets --delete-emptydir-data --grace-period=10 $1"
