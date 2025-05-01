import sqlalchemy as sa
from sqlalchemy.ext import compiler
from sqlalchemy.schema import ExecutableDDLElement
from sqlalchemy.sql.compiler import DDLCompiler


class CreateView(ExecutableDDLElement):
    def __init__(self, name: str, selectable: sa.Select):
        self.name = name
        self.selectable = selectable


class DropView(ExecutableDDLElement):
    def __init__(self, name):
        self.name = name


@compiler.compiles(CreateView)
def _create_view(element: sa.Table, ddlcompiler: DDLCompiler, **kw):
    return "CREATE VIEW %s AS %s" % (
        element.name,
        ddlcompiler.sql_compiler.process(element.selectable, literal_binds=True),
    )


@compiler.compiles(DropView)
def _drop_view(element: sa.Table, ddlcompiler: DDLCompiler, **kw):
    return "DROP VIEW %s" % (element.name)


def _view_exists(ddl, target, bind, **kw):
    return ddl.name in sa.inspect(bind).get_view_names()


def _view_doesnt_exist(ddl, target, connection, **kw):
    return not _view_exists(ddl, target, connection, **kw)


def create_view(name: str, metadata: sa.MetaData, selectable: sa.Select):
    t = sa.table(
        name,
        *(
            sa.Column(c.name, c.type, primary_key=c.primary_key)
            for c in selectable.selected_columns
        ),
    )
    t.primary_key.update(c for c in t.c if c.primary_key)

    sa.event.listen(
        metadata,
        "after_create",
        CreateView(name, selectable).execute_if(callable_=_view_doesnt_exist),
    )
    sa.event.listen(
        metadata,
        "before_drop",
        DropView(name).execute_if(callable_=_view_exists),
    )
    return t


if __name__ == "__main__":
    engine = sa.create_engine("sqlite://", echo=True)
    metadata = sa.MetaData()
    stuff = sa.Table(
        "stuff",
        metadata,
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("data", sa.String(50)),
    )

    more_stuff = sa.Table(
        "more_stuff",
        metadata,
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("stuff_id", sa.Integer, sa.ForeignKey("stuff.id")),
        sa.Column("data", sa.String(50)),
    )

    # the .label() is to suit SQLite which needs explicit label names
    # to be given when creating the view
    # See http://www.sqlite.org/c3ref/column_name.html
    stuff_view = create_view(
        "stuff_view",
        metadata,
        sa.select(
            stuff.c.id.label("id"),
            stuff.c.data.label("data"),
            more_stuff.c.data.label("moredata"),
        )
        .select_from(stuff.join(more_stuff))
        .where(stuff.c.data.like(("%orange%"))),
    )

    assert list(stuff_view.primary_key) == [stuff_view.c.id]

    with engine.begin() as conn:
        metadata.create_all(conn)

    with engine.begin() as conn:
        conn.execute(
            stuff.insert(),
            [
                {"data": "apples"},
                {"data": "pears"},
                {"data": "oranges"},
                {"data": "orange julius"},
                {"data": "apple jacks"},
            ],
        )

        conn.execute(
            more_stuff.insert(),
            [
                {"stuff_id": 3, "data": "foobar"},
                {"stuff_id": 4, "data": "foobar"},
            ],
        )

    with engine.connect() as conn:
        assert conn.execute(
            sa.select(stuff_view.c.data, stuff_view.c.moredata)
        ).all() == [("oranges", "foobar"), ("orange julius", "foobar")]

    # illustrate ORM usage
    from sqlalchemy.orm import declarative_base
    from sqlalchemy.orm import Session

    Base = declarative_base(metadata=metadata)

    class MyStuff(Base):
        __table__ = stuff_view

        def __repr__(self):
            return f"MyStuff({self.id!r}, {self.data!r}, {self.moredata!r})"

    with Session(engine) as s:
        print(s.query(MyStuff).all())
