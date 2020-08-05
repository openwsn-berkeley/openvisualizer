pipeline {
    agent {
        label 'linux && debian'
    }
    stages {
        stage('Test') {
            steps {
                sh 'flake8 > code_format_report.log'
                sh 'python -m pytest tests/ov --junitxml=report.xml -s'
            }
        }
    }
    post {
        always {
            junit 'report.xml'
            archiveArtifacts artifacts: '*.log', onlyIfSuccessful: true
            cleanWs()
        }
    }
}