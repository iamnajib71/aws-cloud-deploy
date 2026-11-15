FROM public.ecr.aws/lambda/python:3.13@sha256:d607579704113c92ee947742c82cb264a6e3077d536a62d092b26bd69af1c17f
ENV RELEASE_HEALTH=healthy
RUN dnf upgrade --releasever=latest --refresh -y && dnf clean all \
    && rm -f /usr/local/bin/aws-lambda-rie
COPY requirements-lock.txt ${LAMBDA_TASK_ROOT}/requirements-lock.txt
RUN pip install --no-cache-dir -r ${LAMBDA_TASK_ROOT}/requirements-lock.txt --target ${LAMBDA_TASK_ROOT} \
    && pip uninstall -y pip setuptools
COPY app ${LAMBDA_TASK_ROOT}/app
USER 10001:10001
CMD ["app.main.handler"]
