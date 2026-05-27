# Movie Filtering Performance Notes

The movie catalog filters use normalized `Genre` and `Language` tables with many-to-many relationships to `Movie`. This avoids comma-separated text filtering and lets the database use indexed join tables when users select multiple genres or languages.

## Query Strategy

- Filters are applied server-side in `movies.views.movie_list`.
- Genre and language filters use indexed slugs through many-to-many joins.
- Sorting is whitelisted to known indexed or stable fields: name, rating, and newest id order.
- Pagination runs after filtering and sorting, so every page reflects the same filter state.
- Movie cards use `prefetch_related("genres", "languages")` to avoid one query per movie.

## Dynamic Counts

Facet counts are computed with conditional `Count(..., filter=...)` annotations:

- Genre counts apply the current search and language filters, but intentionally ignore the selected genre filter.
- Language counts apply the current search and genre filters, but intentionally ignore the selected language filter.

This produces counts that answer: "How many results would remain if I add or remove this option while keeping the other filter group active?"

## Indexing

The migration adds:

- `genre.slug` and `language.slug` indexes for fast filter lookups.
- A `movie.name` index for name sorting and exact/prefix-friendly lookups.
- A composite `movie.rating, movie.name` index for top-rated sorting with deterministic secondary order.
- Django-created foreign key indexes on the many-to-many through tables.

For PostgreSQL catalogs that need fast substring search across tens or hundreds of thousands of movies, add a trigram GIN index on `Movie.name` and possibly `Movie.cast`. A normal B-tree index cannot fully optimize `icontains` searches, so the current implementation favors portability while keeping the schema ready for a PostgreSQL-specific search index.

## Trade-Offs

The normalized schema is slightly more complex than storing text values directly on `Movie`, but it scales better because filter options are deduplicated, indexable, and countable. Counts are calculated dynamically for accuracy; for very large catalogs with high traffic, these counts can be cached per filter combination or refreshed from summary tables, trading freshness for lower query cost.
