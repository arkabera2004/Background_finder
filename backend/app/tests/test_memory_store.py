from app.db.memory_store import RunStore


def test_create_and_get_scoped_to_owner():
    store = RunStore()
    run = store.create(owner_id="user-1", depth="standard")
    assert store.get(run.id, owner_id="user-1") is run


def test_get_returns_none_for_wrong_owner():
    store = RunStore()
    run = store.create(owner_id="user-1", depth="standard")
    assert store.get(run.id, owner_id="user-2") is None


def test_list_for_owner_excludes_other_users():
    store = RunStore()
    store.create(owner_id="user-1", depth="standard")
    store.create(owner_id="user-2", depth="standard")
    assert len(store.list_for_owner("user-1")) == 1
