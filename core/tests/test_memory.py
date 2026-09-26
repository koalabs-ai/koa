from koa_core import memory


def test_add_writes_file_and_index(conn, tmp_path):
    mdir = tmp_path / "memory"
    entry = memory.add(conn, mdir, "user", "Mi Perfil", "quien soy", "cuerpo largo")
    path = mdir / "user-mi-perfil.md"
    assert path.exists()
    assert "name: Mi Perfil" in path.read_text()
    rows = memory.list_all(conn)
    assert len(rows) == 1
    assert rows[0]["name"] == "Mi Perfil"
    assert (mdir / "MEMORY.md").exists()


def test_recall_finds_by_word(conn, tmp_path):
    mdir = tmp_path / "memory"
    memory.add(conn, mdir, "feedback", "bug critico", "se cayo la api", "detalle del bug")
    memory.add(conn, mdir, "project", "otro proyecto", "nada que ver", "texto")
    hits = memory.recall(conn, "critico")
    assert any("bug" in h["name"] for h in hits)


def test_reindex_rebuilds_from_disk(conn, tmp_path):
    mdir = tmp_path / "memory"
    memory.add(conn, mdir, "reference", "algo", "desc", "cuerpo")
    conn.execute("DELETE FROM memory")
    conn.commit()
    n = memory.reindex(conn, mdir)
    assert n == 1
    assert len(memory.list_all(conn)) == 1
