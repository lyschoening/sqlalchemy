"""test the inspection registry system."""

from test.lib.testing import eq_, assert_raises, is_
from sqlalchemy import exc, util
from sqlalchemy import inspect
from test.orm import _fixtures
from sqlalchemy.orm import class_mapper, synonym, Session
from sqlalchemy.orm.attributes import instance_state, NO_VALUE
from test.lib import testing

class TestORMInspection(_fixtures.FixtureTest):
    @classmethod
    def setup_mappers(cls):
        cls._setup_stock_mapping()
        inspect(cls.classes.User).add_property(
            "name_syn",synonym("name")
        )

    def test_class_mapper(self):
        User = self.classes.User

        assert inspect(User) is class_mapper(User)

    def test_instance_state(self):
        User = self.classes.User
        u1 = User()

        assert inspect(u1) is instance_state(u1)

    def test_column_collection_iterate(self):
        User = self.classes.User
        user_table = self.tables.users
        insp = inspect(User)
        eq_(
            list(insp.columns),
            [user_table.c.id, user_table.c.name]
        )
        is_(
            insp.columns.id, user_table.c.id
        )

    def test_primary_key(self):
        User = self.classes.User
        user_table = self.tables.users
        insp = inspect(User)
        eq_(insp.primary_key, 
            (user_table.c.id,)
        )

    def test_local_table(self):
        User = self.classes.User
        user_table = self.tables.users
        insp = inspect(User)
        is_(insp.local_table, user_table)

    def test_property(self):
        User = self.classes.User
        user_table = self.tables.users
        insp = inspect(User)
        is_(insp.attr.id, class_mapper(User).get_property('id'))

    def test_col_property(self):
        User = self.classes.User
        user_table = self.tables.users
        insp = inspect(User)
        id_prop = insp.attr.id

        eq_(id_prop.columns, [user_table.c.id])
        is_(id_prop.expression, user_table.c.id)

        assert not hasattr(id_prop, 'mapper')

    def test_attr_keys(self):
        User = self.classes.User
        insp = inspect(User)
        eq_(
            set(insp.attr.keys()), 
            set(['addresses', 'orders', 'id', 'name', 'name_syn'])
        )

    def test_col_filter(self):
        User = self.classes.User
        insp = inspect(User)
        eq_(
            list(insp.column_attrs),
            [insp.get_property('id'), insp.get_property('name')]
        )
        eq_(
            insp.column_attrs.keys(),
            ['id', 'name']
        )
        is_(
            insp.column_attrs.id,
            User.id.property
        )

    def test_synonym_filter(self):
        User = self.classes.User
        syn = inspect(User).synonyms

        eq_(
            list(syn.keys()), ['name_syn']
        )
        is_(syn.name_syn, User.name_syn.original_property)
        eq_(dict(syn), {
            "name_syn":User.name_syn.original_property
        })

    def test_relationship_filter(self):
        User = self.classes.User
        rel = inspect(User).relationships

        eq_(
            rel.addresses,
            User.addresses.property
        )
        eq_(
            set(rel.keys()), 
            set(['orders', 'addresses'])
        )

    def test_insp_prop(self):
        User = self.classes.User
        prop = inspect(User.addresses)
        is_(prop, User.addresses.property)

    def test_rel_accessors(self):
        User = self.classes.User
        Address = self.classes.Address
        prop = inspect(User.addresses)
        is_(prop.parent, class_mapper(User))
        is_(prop.mapper, class_mapper(Address))

        assert not hasattr(prop, 'columns')
        assert not hasattr(prop, 'expression')

    def test_instance_state(self):
        User = self.classes.User
        u1 = User()
        insp = inspect(u1)
        is_(insp, instance_state(u1))

    def test_instance_state_attr(self):
        User = self.classes.User
        u1 = User(name='ed')
        insp = inspect(u1)

        eq_(
            set(insp.attr.keys()),
            set(['id', 'name', 'name_syn', 'addresses', 'orders'])
        )
        eq_(
            insp.attr.name.value,
            'ed'
        )
        eq_(
            insp.attr.name.loaded_value,
            'ed'
        )

    def test_instance_state_attr_passive_value_scalar(self):
        User = self.classes.User
        u1 = User(name='ed')
        insp = inspect(u1)
        # value was not set, NO_VALUE
        eq_(
            insp.attr.id.loaded_value,
            NO_VALUE
        )
        # regular accessor sets it
        eq_(
            insp.attr.id.value,
            None
        )
        # now the None is there
        eq_(
            insp.attr.id.loaded_value,
            None
        )

    def test_instance_state_attr_passive_value_collection(self):
        User = self.classes.User
        u1 = User(name='ed')
        insp = inspect(u1)
        # value was not set, NO_VALUE
        eq_(
            insp.attr.addresses.loaded_value,
            NO_VALUE
        )
        # regular accessor sets it
        eq_(
            insp.attr.addresses.value,
            []
        )
        # now the None is there
        eq_(
            insp.attr.addresses.loaded_value,
            []
        )

    def test_instance_state_attr_hist(self):
        User = self.classes.User
        u1 = User(name='ed')
        insp = inspect(u1)
        hist = insp.attr.addresses.history
        eq_(
            hist.unchanged, None
        )
        u1.addresses
        hist = insp.attr.addresses.history
        eq_(
            hist.unchanged, []
        )

    def test_instance_state_ident_transient(self):
        User = self.classes.User
        u1 = User(name='ed')
        insp = inspect(u1)
        is_(insp.identity, None)

    def test_instance_state_ident_persistent(self):
        User = self.classes.User
        u1 = User(name='ed')
        s = Session(testing.db)
        s.add(u1)
        s.flush()
        insp = inspect(u1)
        eq_(insp.identity, (u1.id,))
        is_(s.query(User).get(insp.identity), u1)

    def test_identity_key(self):
        User = self.classes.User
        u1 = User(name='ed')
        s = Session(testing.db)
        s.add(u1)
        s.flush()
        insp = inspect(u1)
        eq_(
            insp.identity_key,
            (User, (11, ))
        )

    def test_persistence_states(self):
        User = self.classes.User
        u1 = User(name='ed')
        insp = inspect(u1)

        eq_(
            (insp.transient, insp.pending,
            insp.persistent, insp.detached),
            (True, False, False, False)
        )
        s = Session(testing.db)
        s.add(u1)

        eq_(
            (insp.transient, insp.pending,
            insp.persistent, insp.detached),
            (False, True, False, False)
        )

        s.flush()
        eq_(
            (insp.transient, insp.pending,
            insp.persistent, insp.detached),
            (False, False, True, False)
        )
        s.expunge(u1)
        eq_(
            (insp.transient, insp.pending,
            insp.persistent, insp.detached),
            (False, False, False, True)
        )

    def test_session_accessor(self):
        User = self.classes.User
        u1 = User(name='ed')
        insp = inspect(u1)

        is_(insp.session, None)
        s = Session()
        s.add(u1)
        is_(insp.session, s)

    def test_object_accessor(self):
        User = self.classes.User
        u1 = User(name='ed')
        insp = inspect(u1)
        is_(insp.object, u1)
