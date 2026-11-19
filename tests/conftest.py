import os
from uuid import uuid4

import pytest


@pytest.fixture
def database_url():
    base = os.environ.get("TEST_DATABASE_URL")
    if not base:
        pytest.skip("실제 DB 검증에는 TEST_DATABASE_URL이 필요합니다.")
    psycopg = pytest.importorskip("psycopg")
    from psycopg import sql
    from psycopg.conninfo import make_conninfo

    from finguard.database import initialize

    # 개발용 테이블을 지우지 않고 테스트마다 별도 스키마를 사용한다.
    schema = "test_" + uuid4().hex
    with psycopg.connect(base, autocommit=True) as connection:
        connection.execute(sql.SQL("CREATE SCHEMA {}").format(sql.Identifier(schema)))
    url = make_conninfo(base, options=f"-c search_path={schema}")
    try:
        initialize(url)
        initialize(url)
        yield url
    finally:
        with psycopg.connect(base, autocommit=True) as connection:
            connection.execute(
                sql.SQL("DROP SCHEMA {} CASCADE").format(sql.Identifier(schema))
            )
