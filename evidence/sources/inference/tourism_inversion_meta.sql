-- Model-level summary of the tested-point acceptance mask and warnings.
-- accepted_min_c/accepted_max_c are the extreme ACCEPTED candidates on the
-- prespecified grid, not interval endpoints; NULL when nothing was accepted.
select model_key, outcome, specification, n, clusters, b, se,
       accepted_min_c, accepted_max_c, accepted_count, warnings
from tourism_inversion_meta
order by outcome, specification;
