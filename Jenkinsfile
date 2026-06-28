pipeline {
    agent any
    environment {
        GIT_COMMIT_SHORT = sh(script: 'git rev-parse --short HEAD', returnStdout: true).trim()
    }
    stages {
        stage('Log Commit') {
            steps {
                timeout(time: 1, unit: 'MINUTES') {
                    retry(1) {
                        sh '''
                            echo Current SHA is: $GIT_COMMIT
                            echo Current Short SHA is: ${env.GIT_COMMIT_SHORT}
                        '''
                    }
                }
            }
        }
        stage('Trivy') {
            when {
                changeRequest()
            }
            steps {
                timeout(time: 5, unit: 'MINUTES') {
                    retry(2) {
                        sh '''
                            apt update && apt install -y gnupg curl wget unzip ca-certificates
                            wget -qO - https://aquasecurity.github.io/trivy-repo/deb/public.key | gpg --dearmor | tee /usr/share/keyrings/trivy.gpg > /dev/null
                            echo "deb [signed-by=/usr/share/keyrings/trivy.gpg] https://aquasecurity.github.io/trivy-repo/deb generic main" | tee -a /etc/apt/sources.list.d/trivy.list
                            apt-get update
                            apt-get install trivy -y
                            trivy fs /app --include-dev-deps --dependency-tree
                        '''
                    }
                }
            }
        }
        stage('SBOM - Syft/Grype') {
            when {
                changeRequest()
            }
            steps {
                timeout(time: 5, unit: 'MINUTES') {
                    retry(2) {
                        sh '''
                            apt update && apt install -y gnupg curl wget unzip ca-certificates
                            curl -sSfL https://get.anchore.io/syft | sh -s -- -b /usr/local/bin
                            curl -sSfL https://get.anchore.io/grype | sh -s -- -b /usr/local/bin
                            rm -rf /scans || true
                            mkdir /scans
                            syft /app -o cyclonedx-json=/scans/sbom.json
                            grype sbom:/scans/sbom.json
                        '''
                    }
                }
            }
        }
        stage('Build') {
            when {
                anyOf {
                    branch 'main'
                    branch 'master'
                    branch 'develop'
                }
            }
            steps {
                timeout(time: 10, unit: 'MINUTES') {
                    retry(2) {
                        sh '''
                            docker build -f backend.Dockerfile -t backend/django:$GIT_COMMIT .
                        '''
                    }
                }
            }
        }
        stage('Regression') {
            when {
                allOf {
                    changeRequest()
                    anyOf {
                        changeRequest target: 'main'
                        changeRequest target: 'master'
                    }
                }
            }
            steps {
                timeout(time: 30, unit: 'MINUTES') {
                    retry(0) {
                        sh '''
                            echo "Run Regression Pack"
                        '''
                    }
                }
            }
        }
        stage('DAST') {
            when {
                allOf {
                    changeRequest()
                    anyOf {
                        changeRequest target: 'main'
                        changeRequest target: 'master'
                    }
                }
            }
            steps {
                timeout(time: 30, unit: 'MINUTES') {
                    retry(0) {
                        sh '''
                            git clone https://github.com/projectdiscovery/nuclei.git;
                            cd nuclei/cmd/nuclei;
                            go build;
                            mv nuclei /usr/local/bin/;
                            nuclei -version;
                        '''
                    }
                }
            }
        }
        stage('Secrets - NonProd') {
            when {
                branch 'develop'
            }
            steps {
                timeout(time: 10, unit: 'MINUTES') {
                    retry(1) {
                        sh '''
                            echo "Push secrets to Non-Prod Secrets Server with version $GIT_COMMIT"
                        '''
                    }
                }
            }
        }
        stage('Secrets - Prod') {
            when {
                anyOf {
                    branch 'main'
                    branch 'master'
                }
            }
            steps {
                timeout(time: 10, unit: 'MINUTES') {
                    retry(1) {
                        sh '''
                            echo "Push secrets to Prod Secrets Server with version $GIT_COMMIT"
                        '''
                    }
                }
            }
        }
        stage('ArgoCD - NonProd') {
            when {
                branch 'develop'
            }
            steps {
                timeout(time: 10, unit: 'MINUTES') {
                    retry(1) {
                        sh '''
                            argocd app sync argocd/booking-backend-dev
                        '''
                    }
                }
            }
        }
        stage('ArgoCD - Prod') {
            when {
                anyOf {
                    branch 'main'
                    branch 'master'
                }
            }
            steps {
                timeout(time: 10, unit: 'MINUTES') {
                    retry(1) {
                        sh '''
                            argocd app sync argocd/booking-backend-prod
                        '''
                    }
                }
            }
        }
    }
}
