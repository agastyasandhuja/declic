# API service

Proposed Python/FastAPI modular backend. Not initialized yet.
Agastya owns core, main.py, workers and shared Python dependencies.
Adi owns auth/entertainment; Amogh owns canvas/curriculum.

MongoDB Atlas is the adopted application database; Supabase provides app Auth and
object storage. Agastya owns the shared Atlas connection, Python driver and ordered
database changes. Domain owners draft collections/validators/indexes under their
database domains. Mobile clients never connect to Atlas; protected routes derive
ownership from verified Supabase access tokens. See the [database setup plan](../../database/README.md).
No live database connection or executable database setup exists yet.

Each domain exports a router and service interface. Core registers them.
See [integration](../../docs/INTEGRATION.md) and [contracts](../../contracts/README.md).

Add install, environment, run, worker and test commands when initialized.
