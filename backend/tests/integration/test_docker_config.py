import os

import yaml


def test_dockerfile_contents():
    # Verify backend/Dockerfile exists
    dockerfile_path = os.path.join(os.path.dirname(__file__), "..", "..", "Dockerfile")
    assert os.path.exists(dockerfile_path)

    with open(dockerfile_path, encoding="utf-8") as f:
        content = f.read()

    # Basic validations
    assert "FROM" in content
    assert "WORKDIR" in content
    assert "COPY" in content


def test_docker_compose_structure():
    # Verify root docker-compose.yml exists
    compose_path = os.path.join(os.path.dirname(__file__), "..", "..", "..", "docker-compose.yml")
    assert os.path.exists(compose_path)

    with open(compose_path, encoding="utf-8") as f:
        config = yaml.safe_load(f)

    # Basic compose validations
    assert "services" in config
    services = config["services"]

    assert "postgres" in services
    assert "redis" in services
    assert "backend" in services
    assert "worker" in services

    # Verify pgvector postgres image
    assert "pgvector/pgvector" in services["postgres"]["image"]
