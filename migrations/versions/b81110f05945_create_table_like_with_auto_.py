"""Create table like with auto-incrementing id

Revision ID: b81110f05945
Revises: 4da2e569e4b1
Create Date: 2024-09-09 20:21:05.509072

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'b81110f05945'
down_revision = '4da2e569e4b1'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('like', schema=None) as batch_op:
        batch_op.alter_column('post_id',
               existing_type=sa.INTEGER(),
               nullable=False)
        batch_op.drop_index('ix_like_timestamp')

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('like', schema=None) as batch_op:
        batch_op.create_index('ix_like_timestamp', ['timestamp'], unique=False)
        batch_op.alter_column('post_id',
               existing_type=sa.INTEGER(),
               nullable=True)

    # ### end Alembic commands ###