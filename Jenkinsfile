pipeline {
    agent any
    stages {
        stage('Deploy') {
            steps {
                sh 'echo Deploying....'
                sh 'ssh vitel@38.143.106.249 -o StrictHostKeyChecking=no "export APP_ENV=dev && bash /var/www/html/hrms/src/deploy.sh "'
            }
        }
    }
}