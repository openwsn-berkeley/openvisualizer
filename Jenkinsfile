pipeline {
    agent {
        label 'linux && debian'
    }
    stages {
        stage('Test') {
            steps {
                sh 'flake8 > format_checking.txt'
                sh 'pytest tests/ov --junitxml=report.xml -s'
            }
        }
    }
    post {
        always {
            junit 'report.xml'
            archiveArtifacts artifacts: '*.txt', onlyIfSuccessful: true
            cleanWs()
        }
    }
}