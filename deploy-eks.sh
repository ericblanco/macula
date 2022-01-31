#!/bin/bash


# stop on error
set -e


# source Variables/config file
source deploy-scripts/config



#Display how to use deploy-eks.sh 
Help()
{
   # Display Help
   echo "Deploy given branch to EKS Cluster"
   echo
   echo "options:"
   echo "h     Print this Help."
   echo "v     Verbose mode to use please use at end i.e ./deploy-eks.sh <env> <branch> -v."
   echo "a     Specifiy Application Env i.e stga stg1"
}


#Parse Variables
while getopts "a:hv" option; do
   case $option in
      h) # display Help
         Help
         exit;;
      v) # Verbose Mode
	 echo "DEBUG MODE"
         set -x;;
      a) # Specify App Env
	 TARGET_ENV=${OPTARG};;
     \?) # incorrect option
         echo "Error: Invalid option"
         exit;;
   esac
done


#Check Deploy environment i.e staging/prod/dr/svl
case $CURRENT_HOST in
	$STAGING_PRIVATE_DNS_NAME)  
		ECRPATH=$ECRPATH_STAGING ;
		ECR=$ECR_STAGING ;
		DOCKER_FILE=Dockerfile ;;
	$PRODUCTION_PRIVATE_DNS_NAME)
		ECRPATH=$ECRPATH_PROD ;
		ECR=$ECR_PROD ;
		DOCKER_FILE=Dockerfile ;;
	$DR_PRIVATE_DNS_NAME)
		ECRPATH=$ECRPATH_DR ;
		ECR=$ECR_DR ;
		DOCKER_FILE=Dockerfile ;
		REGION=us-west-2;;
	$SVL_PRIVATE_DNS_NAME)
		ECRPATH=$ECRPATH_SVL ;
		ECR=$ECR_SVL ;
		DOCKER_FILE=Dockerfile ;;
	*)
		echo "ERROR:  not running in any valid deployment server"
		exit 1 ;;
esac

# Clone Branch into tmp
mkdir ${TARGET_DIR} && cd "$_"
git clone ${APPROOT_REPO}/${TARGET_APP} -b ${TARGET_BRANCH}
cd ${TARGET_APP}

# Build Docker Container
chmod 755 deploy-scripts/load_ssm_wrapper

# Convert Target_app var to match ecr + ssm repo names
TARGET_APP=`echo ${TARGET_APP} | tr '[:upper:]' '[:lower:]'`
docker build -f deploy-scripts/${DOCKER_FILE} -t ${TARGET_APP}/builder:${TARGET_IMAGE} .

# Login to ECR REPO
$(aws ecr get-login --no-include-email --region ${REGION})

# Tag Containers
docker tag ${TARGET_APP}/builder:${TARGET_IMAGE} ${ECR}/${TARGET_APP}/${ECRPATH}:${TARGET_IMAGE}
docker tag ${TARGET_APP}/builder:${TARGET_IMAGE} ${ECR}/${TARGET_APP}/${ECRPATH}:${LATEST_TAG}

# Push Containers
docker push ${ECR}/${TARGET_APP}/${ECRPATH}:${TARGET_IMAGE}
docker push ${ECR}/${TARGET_APP}/${ECRPATH}:${LATEST_TAG}

# Ouptut Container Name
echo
echo "** IMAGE: ${ECR}/${TARGET_APP}/${ECRPATH}:${TARGET_IMAGE}"

#clean up files
rm -rf ${TARGET_DIR}
