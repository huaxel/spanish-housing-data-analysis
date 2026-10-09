-- Prespecified wild-bootstrap candidate grid (tested points only).
-- keep_95 is the acceptance mask at the nominal 95% level per candidate;
-- it is not a continuous confidence interval.
select model_key, outcome, specification, candidate_c, wild_p, keep_95
from tourism_inversion
order by outcome, specification, candidate_c;
