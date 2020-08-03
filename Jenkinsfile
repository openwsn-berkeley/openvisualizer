pipeline {
    agent {
        label 'linux && debian'
    }
    stages {
        stage('Test') {
            steps {
                sh 'python --version'
                sh 'sudo python -m pytest tests/ov --junitxml=report.xml -s'
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