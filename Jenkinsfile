pipeline {
    agent any

    environment {
        COMPOSE_PROJECT = 'devops-flask-pipeline'
        EC2_HOST = '13.127.187.14'
        EC2_PROJECT = '/home/ubuntu/devops-flask-project'
        AWS_REGION = 'ap-south-1'
        ALB_NAME = 'devops-flask-alb'
    }

    stages {

        // ============================================================
        // 1. TEST EC2 SSH
        // ============================================================

        stage('Test EC2 SSH Access then list project directory and Docker services') {
            steps {
                withCredentials([
                    sshUserPrivateKey(
                        credentialsId: 'ec2-deploy-key',
                        keyFileVariable: 'SSH_KEY',
                        usernameVariable: 'SSH_USER'
                    )
                ]) {
                    sh '''
                        ssh -o StrictHostKeyChecking=no \
                        -i "$SSH_KEY" \
                        "$SSH_USER@$EC2_HOST" \
                        "whoami && \
                        hostname && \
                        cd $EC2_PROJECT && \
                        pwd && \
                        ls -la && \
                        docker compose ps && \
                        docker compose config --services"
                    '''
                }
            }
        }

        // ============================================================
        // 2. TEST AWS
        // ============================================================

        stage('Test AWS Access') {
            steps {
                withCredentials([
                    usernamePassword(
                        credentialsId: 'aws-jenkins-deployer',
                        usernameVariable: 'AWS_ACCESS_KEY_ID',
                        passwordVariable: 'AWS_SECRET_ACCESS_KEY'
                    )
                ]) {
                    sh '''
                        aws sts get-caller-identity

                        echo "Checking ALB target groups..."

                        aws elbv2 describe-target-groups \
                            --region "$AWS_REGION" \
                            --query 'TargetGroups[].{Name:TargetGroupName,Arn:TargetGroupArn}' \
                            --output table
                    '''
                }
            }
        }


        // ============================================================
        // 3. DETECT CURRENT ALB ENVIRONMENT
        // ============================================================

        stage('Detect ALB Active Environment') {
            steps {
                withCredentials([
                    usernamePassword(
                        credentialsId: 'aws-jenkins-deployer',
                        usernameVariable: 'AWS_ACCESS_KEY_ID',
                        passwordVariable: 'AWS_SECRET_ACCESS_KEY'
                    )
                ]) {
                    script {
                        def ACTIVE_TG = sh(
                            script: '''
                                aws elbv2 describe-listeners \
                                    --region "$AWS_REGION" \
                                    --load-balancer-arn $(aws elbv2 describe-load-balancers \
                                        --region "$AWS_REGION" \
                                        --names "$ALB_NAME" \
                                        --query 'LoadBalancers[0].LoadBalancerArn' \
                                        --output text) \
                                    --query 'Listeners[0].DefaultActions[0].TargetGroupArn' \
                                    --output text
                            ''',
                            returnStdout: true
                        ).trim()

                        echo "Active ALB Target Group ARN: ${ACTIVE_TG}"

                        if (ACTIVE_TG.contains('devops-flask-green-tg')) {

                            echo "🟢 ALB is currently pointing to GREEN"

                        } else if (ACTIVE_TG.contains('devops-flask-tg')) {

                            echo "🔵 ALB is currently pointing to BLUE"

                        } else {

                            error "Unknown ALB target group: ${ACTIVE_TG}"

                        }
                    }
                }
            }
        }


        // ============================================================
        // 4. SWITCH ALB TRAFFIC
        // ============================================================

        stage('Switch ALB Traffic') {
            steps {
                withCredentials([
                    usernamePassword(
                        credentialsId: 'aws-jenkins-deployer',
                        usernameVariable: 'AWS_ACCESS_KEY_ID',
                        passwordVariable: 'AWS_SECRET_ACCESS_KEY'
                    )
                ]) {
                    script {

                        def ALB_ARN = sh(
                            script: '''
                                aws elbv2 describe-load-balancers \
                                    --region "$AWS_REGION" \
                                    --names "$ALB_NAME" \
                                    --query 'LoadBalancers[0].LoadBalancerArn' \
                                    --output text
                            ''',
                            returnStdout: true
                        ).trim()


                        def LISTENER_ARN = sh(
                            script: """
                                aws elbv2 describe-listeners \
                                    --region "$AWS_REGION" \
                                    --load-balancer-arn '${ALB_ARN}' \
                                    --query 'Listeners[0].ListenerArn' \
                                    --output text
                            """,
                            returnStdout: true
                        ).trim()
                        def CURRENT_TG = sh(
                            script: """
                                aws elbv2 describe-listeners \
                                    --region "$AWS_REGION" \
                                    --listener-arns '${LISTENER_ARN}' \
                                    --query 'Listeners[0].DefaultActions[0].TargetGroupArn' \
                                    --output text
                            """,
                            returnStdout: true
                        ).trim()

                        echo "Current Target Group: ${CURRENT_TG}"


                        def TARGET_TG = ''


                        if (CURRENT_TG.contains('devops-flask-green-tg')) {

                            echo "🟢 GREEN is active"
                            echo "Switching traffic GREEN → BLUE"

                            TARGET_TG = sh(
                                script: '''
                                    aws elbv2 describe-target-groups \
                                        --region "$AWS_REGION" \
                                        --names devops-flask-tg \
                                        --query 'TargetGroups[0].TargetGroupArn' \
                                        --output text
                                ''',
                                returnStdout: true
                            ).trim()


                        } else if (CURRENT_TG.contains('devops-flask-tg')) {

                            echo "🔵 BLUE is active"
                            echo "Switching traffic BLUE → GREEN"

                            TARGET_TG = sh(
                                script: '''
                                    aws elbv2 describe-target-groups \
                                        --region "$AWS_REGION" \
                                        --names devops-flask-green-tg \
                                        --query 'TargetGroups[0].TargetGroupArn' \
                                        --output text
                                ''',
                                returnStdout: true
                            ).trim()


                        } else {

                            error "Unknown current target group: ${CURRENT_TG}"

                        }


                        echo "New Target Group: ${TARGET_TG}"


                        sh """
                            aws elbv2 modify-listener \
                                --region "$AWS_REGION" \
                                --listener-arn '${LISTENER_ARN}' \
                                --default-actions Type=forward,TargetGroupArn='${TARGET_TG}'
                        """


                        echo "ALB traffic switch completed."


                        def VERIFIED_TG = sh(
                            script: """
                                aws elbv2 describe-listeners \
                                    --region "$AWS_REGION" \
                                    --listener-arns '${LISTENER_ARN}' \
                                    --query 'Listeners[0].DefaultActions[0].TargetGroupArn' \
                                    --output text
                            """,
                            returnStdout: true
                        ).trim()


                        echo "Verified Target Group: ${VERIFIED_TG}"


                        if (VERIFIED_TG != TARGET_TG) {

                            error "ALB traffic switch verification failed!"

                        }


                        echo "✅ ALB traffic switch verified successfully."
                    }
                }
            }
        }


        // ============================================================
        // 5. CALCULATE BUILD VERSION
        // ============================================================

        stage('Calculate the version of the build') {
            steps {
                script {

                    def GIT_HASH = sh(
                        script: 'git rev-parse --short HEAD',
                        returnStdout: true
                    ).trim()

                    echo "Git Hash: ${GIT_HASH}"

                    sh 'pwd'
                }
            }
        }


        // ============================================================
        // 6. DEPLOY APPLICATION TO EC2
        // ============================================================

        stage('Deploy Application') {
            steps {

                withCredentials([
                    sshUserPrivateKey(
                        credentialsId: 'ec2-deploy-key',
                        keyFileVariable: 'SSH_KEY',
                        usernameVariable: 'SSH_USER'
                    )
                ]) {

                    script {

                        // Find the environment currently receiving
                        // application traffic through EC2 Nginx.

                        def ACTIVE_ENV = sh(
                            script: '''
                                ssh -o StrictHostKeyChecking=no \
                                    -i "$SSH_KEY" \
                                    "$SSH_USER@$EC2_HOST" \
                                    "cd $EC2_PROJECT && \
                                    docker compose exec -T nginx nginx -T 2>/dev/null |
                                    grep 'proxy_pass http://flask-' |
                                    head -n 1"
                            ''',
                            returnStdout: true
                        ).trim()


                        if (ACTIVE_ENV.contains('flask-green:5000')) {

                            ACTIVE_ENV = 'GREEN'

                        } else if (ACTIVE_ENV.contains('flask-blue:5000')) {

                            ACTIVE_ENV = 'BLUE'

                        } else {

                            error 'Could not determine active environment on EC2'

                        }


                        echo "Currently active environment on EC2: ${ACTIVE_ENV}"


                        // Make sure MySQL is running.

                        sh '''
                            ssh -o StrictHostKeyChecking=no \
                                -i "$SSH_KEY" \
                                "$SSH_USER@$EC2_HOST" \
                                "cd $EC2_PROJECT && \
                                docker compose up -d mysql"
                        '''


                        if (ACTIVE_ENV == 'BLUE') {

                            echo 'BLUE is currently active.'
                            echo 'Deploying GREEN on EC2.'

                            sh '''
                                ssh -o StrictHostKeyChecking=no \
                                    -i "$SSH_KEY" \
                                    "$SSH_USER@$EC2_HOST" \
                                    "cd $EC2_PROJECT && \
                                    docker compose build flask-green && \
                                    docker compose up -d flask-green"
                            '''


                        } else if (ACTIVE_ENV == 'GREEN') {

                            echo 'GREEN is currently active.'
                            echo 'Deploying BLUE on EC2.'

                            sh '''
                                ssh -o StrictHostKeyChecking=no \
                                    -i "$SSH_KEY" \
                                    "$SSH_USER@$EC2_HOST" \
                                    "cd $EC2_PROJECT && \
                                    docker compose build flask-blue && \
                                    docker compose up -d flask-blue"
                            '''


                        } else {

                            error "Invalid active environment: ${ACTIVE_ENV}"

                        }
                    }
                }
            }
        }


        // ============================================================
        // 7. HEALTH CHECK NEW ENVIRONMENT ON EC2
        // ============================================================

        stage('Health Check New Environment') {
            steps {

                withCredentials([
                    sshUserPrivateKey(
                        credentialsId: 'ec2-deploy-key',
                        keyFileVariable: 'SSH_KEY',
                        usernameVariable: 'SSH_USER'
                    )
                ]) {

                    script {

                        def ACTIVE_ENV = sh(
                            script: '''
                                ssh -o StrictHostKeyChecking=no \
                                    -i "$SSH_KEY" \
                                    "$SSH_USER@$EC2_HOST" \
                                    "cd $EC2_PROJECT && \
                                    docker compose exec -T nginx nginx -T 2>/dev/null |
                                    grep -q 'proxy_pass http://flask-green:5000;' &&
                                    echo GREEN ||
                                    echo BLUE"
                            ''',
                            returnStdout: true
                        ).trim()


                        echo "Currently active environment on EC2: ${ACTIVE_ENV}"


                        if (ACTIVE_ENV == 'BLUE') {

                            echo 'Checking GREEN on EC2.'

                            sh '''
                                ssh -o StrictHostKeyChecking=no \
                                    -i "$SSH_KEY" \
                                    "$SSH_USER@$EC2_HOST" \
                                    "cd $EC2_PROJECT && \
                                    docker compose exec -T flask-green \
                                    python -c \\"import urllib.request; urllib.request.urlopen('http://localhost:5000')\\""
                            '''


                        } else if (ACTIVE_ENV == 'GREEN') {

                            echo 'Checking BLUE on EC2.'

                            sh '''
                                ssh -o StrictHostKeyChecking=no \
                                    -i "$SSH_KEY" \
                                    "$SSH_USER@$EC2_HOST" \
                                    "cd $EC2_PROJECT && \
                                    docker compose exec -T flask-blue \
                                    python -c \\"import urllib.request; urllib.request.urlopen('http://localhost:5000')\\""
                            '''


                        } else {

                            error "Invalid active environment: ${ACTIVE_ENV}"

                        }
                    }
                }
            }
        }


        // ============================================================
        // 8. SWITCH NGINX TRAFFIC ON EC2
        // ============================================================

        stage('Switch Traffic and Verify') {
            steps {

                withCredentials([
                    sshUserPrivateKey(
                        credentialsId: 'ec2-deploy-key',
                        keyFileVariable: 'SSH_KEY',
                        usernameVariable: 'SSH_USER'
                    )
                ]) {

                    script {

                        def ACTIVE_ENV = sh(
                            script: '''
                                ssh -o StrictHostKeyChecking=no \
                                    -i "$SSH_KEY" \
                                    "$SSH_USER@$EC2_HOST" \
                                    "cd $EC2_PROJECT && \
                                    docker compose exec -T nginx nginx -T 2>/dev/null |
                                    grep -q 'proxy_pass http://flask-green:5000;' &&
                                    echo GREEN ||
                                    echo BLUE"
                            ''',
                            returnStdout: true
                        ).trim()


                        try {

                            if (ACTIVE_ENV == 'BLUE') {

                                echo 'Switching Nginx traffic: BLUE → GREEN'

                                sh '''
                                    ssh -o StrictHostKeyChecking=no \
                                        -i "$SSH_KEY" \
                                        "$SSH_USER@$EC2_HOST" \
                                        "cd $EC2_PROJECT && \
                                        sed -i 's/flask-blue:5000/flask-green:5000/' nginx/nginx.conf && \
                                        docker cp nginx/nginx.conf \
                                        devops-flask-project-nginx-1:/etc/nginx/nginx.conf && \
                                        docker compose exec -T nginx nginx -t && \
                                        docker compose exec -T nginx nginx -s reload"
                                '''


                                echo 'Verifying GREEN traffic on EC2.'

                                sh '''
                                    ssh -o StrictHostKeyChecking=no \
                                        -i "$SSH_KEY" \
                                        "$SSH_USER@$EC2_HOST" \
                                        "cd $EC2_PROJECT && \
                                        docker compose exec -T nginx nginx -T |
                                        grep 'proxy_pass http://flask-green:5000;'"
                                '''


                            } else if (ACTIVE_ENV == 'GREEN') {

                                echo 'Switching Nginx traffic: GREEN → BLUE'

                                sh '''
                                    ssh -o StrictHostKeyChecking=no \
                                        -i "$SSH_KEY" \
                                        "$SSH_USER@$EC2_HOST" \
                                        "cd $EC2_PROJECT && \
                                        sed -i 's/flask-green:5000/flask-blue:5000/' nginx/nginx.conf && \
                                        docker cp nginx/nginx.conf \
                                        devops-flask-project-nginx-1:/etc/nginx/nginx.conf && \
                                        docker compose exec -T nginx nginx -t && \
                                        docker compose exec -T nginx nginx -s reload"
                                '''


                                echo 'Verifying BLUE traffic on EC2.'

                                sh '''
                                    ssh -o StrictHostKeyChecking=no \
                                        -i "$SSH_KEY" \
                                        "$SSH_USER@$EC2_HOST" \
                                        "cd $EC2_PROJECT && \
                                        docker compose exec -T nginx nginx -T |
                                        grep 'proxy_pass http://flask-blue:5000;'"
                                '''


                            } else {

                                error "Invalid active environment: ${ACTIVE_ENV}"

                            }


                        } catch (err) {

                            echo 'Traffic verification failed!'
                            echo 'Starting rollback.'


                            if (ACTIVE_ENV == 'BLUE') {

                                echo 'Rolling back: GREEN → BLUE'

                                sh '''
                                    ssh -o StrictHostKeyChecking=no \
                                        -i "$SSH_KEY" \
                                        "$SSH_USER@$EC2_HOST" \
                                        "cd $EC2_PROJECT && \
                                        sed -i 's/flask-green:5000/flask-blue:5000/' nginx/nginx.conf && \
                                        docker cp nginx/nginx.conf \
                                        devops-flask-project-nginx-1:/etc/nginx/nginx.conf && \
                                        docker compose exec -T nginx nginx -t && \
                                        docker compose exec -T nginx nginx -s reload"
                                '''


                            } else if (ACTIVE_ENV == 'GREEN') {

                                echo 'Rolling back: BLUE → GREEN'

                                sh '''
                                    ssh -o StrictHostKeyChecking=no \
                                        -i "$SSH_KEY" \
                                        "$SSH_USER@$EC2_HOST" \
                                        "cd $EC2_PROJECT && \
                                        sed -i 's/flask-blue:5000/flask-green:5000/' nginx/nginx.conf && \
                                        docker cp nginx/nginx.conf \
                                        devops-flask-project-nginx-1:/etc/nginx/nginx.conf && \
                                        docker compose exec -T nginx nginx -t && \
                                        docker compose exec -T nginx nginx -s reload"
                                '''
                            }


                            echo 'Rollback completed.'

                            throw err
                        }
                    }
                }
            }
        }


        // ============================================================
        // 9. CLEANUP OLD ENVIRONMENT ON EC2
        // ============================================================

        stage('Cleanup Old Environment') {
            steps {

                withCredentials([
                    sshUserPrivateKey(
                        credentialsId: 'ec2-deploy-key',
                        keyFileVariable: 'SSH_KEY',
                        usernameVariable: 'SSH_USER'
                    )
                ]) {

                    script {

                        def ACTIVE_ENV = sh(
                            script: '''
                                ssh -o StrictHostKeyChecking=no \
                                    -i "$SSH_KEY" \
                                    "$SSH_USER@$EC2_HOST" \
                                    "cd $EC2_PROJECT && \
                                    docker compose exec -T nginx nginx -T 2>/dev/null |
                                    grep -q 'proxy_pass http://flask-green:5000;' &&
                                    echo GREEN ||
                                    echo BLUE"
                            ''',
                            returnStdout: true
                        ).trim()


                        if (ACTIVE_ENV == 'GREEN') {

                            echo 'GREEN is active and verified.'
                            echo 'Stopping old BLUE environment.'

                            sh '''
                                ssh -o StrictHostKeyChecking=no \
                                    -i "$SSH_KEY" \
                                    "$SSH_USER@$EC2_HOST" \
                                    "cd $EC2_PROJECT && \
                                    docker compose stop flask-blue"
                            '''


                        } else if (ACTIVE_ENV == 'BLUE') {

                            echo 'BLUE is active and verified.'
                            echo 'Stopping old GREEN environment.'

                            sh '''
                                ssh -o StrictHostKeyChecking=no \
                                    -i "$SSH_KEY" \
                                    "$SSH_USER@$EC2_HOST" \
                                    "cd $EC2_PROJECT && \
                                    docker compose stop flask-green"
                            '''


                        } else {

                            error "Invalid active environment: ${ACTIVE_ENV}"

                        }
                    }
                }
            }
        }


        // ============================================================
        // 10. BUILD ARTIFACT
        // ============================================================

        stage('Create Build Artifact') {
            steps {
                script {

                    writeFile(
                        file: 'build-info.txt',
                        text: """Build Number: ${BUILD_NUMBER}
                        Git Commit: ${GIT_COMMIT}
                        """
                    )
                }
            }
        }


        // ============================================================
        // 11. ARCHIVE ARTIFACT
        // ============================================================

        stage('Archive Artifact') {
            steps {
                archiveArtifacts artifacts: 'build-info.txt'
            }
        }


        // ============================================================
        // 12. WAIT FOR SERVICES
        // ============================================================

        stage('Wait for Services') {
            steps {
                sh 'sleep 10'
            }
        }


        // ============================================================
        // 13. FINAL HEALTH CHECK
        // ============================================================

        stage('Final Health Check') {
            steps {

                withCredentials([
                    sshUserPrivateKey(
                        credentialsId: 'ec2-deploy-key',
                        keyFileVariable: 'SSH_KEY',
                        usernameVariable: 'SSH_USER'
                    )
                ]) {

                    sh '''
                        ssh -o StrictHostKeyChecking=no \
                            -i "$SSH_KEY" \
                            "$SSH_USER@$EC2_HOST" \
                            "curl --fail --silent http://localhost/"
                    '''
                }
            }
        }
    }


    // ================================================================
    // POST
    // ================================================================

    post {

        success {
            echo 'Pipeline completed successfully!'
        }

        failure {
            echo 'Pipeline failed!'
        }

        always {
            echo 'Pipeline finished.'
        }
    }
}