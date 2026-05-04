warning: in the working copy of 'DECISIONS.md', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'README.md', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'alembic.ini', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'alembic/README', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'alembic/env.py', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'alembic/versions/3adc8f74c2ea_initial_schema.py', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'docker-compose.yml', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'pyproject.toml', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'uv.lock', LF will be replaced by CRLF the next time Git touches it
 DECISIONS.md                                    |   2 [32m+[m[31m-[m
 README.md                                       |   2 [32m+[m[31m-[m
 alembic.ini                                     |   2 [32m+[m[31m-[m
 alembic/README                                  |   2 [32m+[m[31m-[m
 alembic/env.py                                  |   2 [32m+[m[31m-[m
 alembic/versions/3adc8f74c2ea_initial_schema.py |   2 [32m+[m[31m-[m
 app/config.py                                   |   2 [32m+[m[31m-[m
 app/database.py                                 |   2 [32m+[m[31m-[m
 app/main.py                                     |   4 [32m+[m[31m-[m
 app/models/__init__.py                          |   2 [32m+[m[31m-[m
 app/models/employee.py                          |   6 [32m+[m[31m-[m
 app/models/health_record.py                     |  24 [32m++[m[31m--[m
 app/models/product.py                           |  10 [32m+[m[31m-[m
 app/models/product_tag.py                       |   2 [32m+[m[31m-[m
 app/models/recommendation.py                    |  10 [32m+[m[31m-[m
 app/repositories/__init__.py                    |   2 [32m+[m[31m-[m
 app/repositories/employee_repo.py               |   3 [32m+[m[31m-[m
 app/repositories/product_repo.py                |   6 [32m+[m[31m-[m
 app/routers/__init__.py                         |   2 [32m+[m[31m-[m
 app/routers/employees.py                        |   2 [32m+[m[31m-[m
 app/routers/health.py                           |   6 [32m+[m[31m-[m
 app/routers/products.py                         |   2 [32m+[m[31m-[m
 app/routers/recommendations.py                  |   2 [32m+[m[31m-[m
 app/schemas/__init__.py                         |   2 [32m+[m[31m-[m
 app/schemas/employee.py                         |   2 [32m+[m[31m-[m
 app/schemas/health_record.py                    |   2 [32m+[m[31m-[m
 app/schemas/product.py                          |   2 [32m+[m[31m-[m
 app/schemas/recommendation.py                   |   2 [32m+[m[31m-[m
 app/services/__init__.py                        |   2 [32m+[m[31m-[m
 app/services/employee_service.py                |   2 [32m+[m[31m-[m
 app/services/product_service.py                 |   2 [32m+[m[31m-[m
 app/services/recommender.py                     |  22 [32m++[m[31m--[m
 app/services/scoring.py                         |  23 [32m++[m[31m--[m
 docker-compose.yml                              |   2 [32m+[m[31m-[m
 pyproject.toml                                  |  33 [32m+++++[m
 scripts/seed_data.py                            | 154 [32m+++++++++++++++[m[31m---------[m
 uv.lock                                         | 100 [32m+++++++++++++++[m
 37 files changed, 302 insertions(+), 147 deletions(-)
