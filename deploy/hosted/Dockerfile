# ccp hosted service: Django (gunicorn) and django-tasks workers.
#
# REFPROP is not part of the image (NIST licence). Mount a Linux build at
# /opt/refprop (librefprop.so plus FLUIDS/ and MIXTURES/); without it ccp
# falls back to CoolProp.
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    CCP_PROFILE=hosted \
    RPPREFIX=/opt/refprop \
    CCP_STATIC_ROOT=/var/lib/ccp/static \
    CCP_MEDIA_ROOT=/var/lib/ccp/media

RUN apt-get update -q \
    && apt-get install -y -q --no-install-recommends libgfortran5 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY pyproject.toml README.md MANIFEST.in ./
COPY ccp ./ccp
COPY ccp_web ./ccp_web
RUN pip install --no-cache-dir ".[hosted]"

# collectstatic needs a secret key but no database.
RUN CCP_SECRET_KEY=build ccp-web manage collectstatic --noinput

RUN useradd --create-home ccp && mkdir -p /var/lib/ccp/media && chown -R ccp /var/lib/ccp
USER ccp

EXPOSE 8000
CMD ["gunicorn", "ccp_web.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3", "--threads", "4", "--timeout", "120"]
