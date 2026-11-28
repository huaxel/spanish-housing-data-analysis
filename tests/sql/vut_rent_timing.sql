-- Reference for the 2020–24 timing check. Reads the publisher CSVs and
-- SERPAVI parquet directly; does not use the analysis mart, ranks, or window builder.
with homes as (
    select left(Municipios, 5) code, replace(Total, '.', '')::bigint dwellings
    from read_csv(?, delim='\t', all_varchar=true)
    where regexp_matches(Municipios, '^[0-9]{5} ') and Municipios not like '% Resto %'
      and "Consumo eléctrico"='Viviendas totales'
), tourist as (
    select left(Municipios, 5) code, left(Periodo, 4)::int yr,
           try_cast(replace(Total, '.', '') as bigint) stock
    from read_csv(?, delim=';', all_varchar=true)
    where regexp_matches(Municipios, '^[0-9]{5} ') and "Viviendas y plazas"='Viviendas turísticas'
      and Periodo in ('2020M08', '2021M08', '2022M08')
), idx as (
    select left(Municipio, 5) code, Periodo::int yr,
           try_cast(replace(Total, ',', '.') as decimal(12,6)) price_index
    from read_csv(?, delim=';', all_varchar=true)
    where regexp_matches(Municipio, '^[0-9]{5} ') and "Tipo de dato"='Índice'
      and Periodo in ('2022', '2023', '2024')
), rents as (
    select codigo code, anyo yr, price_index,
           case when medida='ALQM2_LV_M_VC' then valor::varchar::decimal(19,16) end rent
    from read_parquet(?) join idx on codigo=idx.code and anyo=idx.yr
    where medida='ALQM2_LV_M_VC' and price_index>0 and valor>0
), eligible as (
    select * from homes where dwellings>0
      and code in (select code from tourist where stock>=0 group by code having count(distinct yr)=3)
      and code in (select code from rents group by code having count(distinct yr)=3)
), endpoints as (
    select s, r, span, e.code, dwellings, t1.stock-t0.stock dn, r0.rent s0, r1.rent s1,
           r0.price_index i0, r1.price_index i1
    from eligible e cross join (values (2020, 2022, 1), (2020, 2023, 1),
                                       (2021, 2023, 1), (2020, 2023, 2)) windows(s,r,span)
    join tourist t0 on t0.code=e.code and t0.yr=s
    join tourist t1 on t1.code=e.code and t1.yr=s+span
    join rents r0 on r0.code=e.code and r0.yr=r
    join rents r1 on r1.code=e.code and r1.yr=r+1
), ranks as (
    -- Pairwise ratio comparisons by cross multiplication, never float division.
    -- Midrank minus one half = # smaller + one half of # equal (including self).
    select a.s, a.r, a.span, a.code,
        sum(case when a.dn*b.dwellings>b.dn*a.dwellings then 1 when a.dn*b.dwellings=b.dn*a.dwellings then 0.5 else 0 end) x,
        sum(case when a.s1*b.s0>b.s1*a.s0 then 1 when a.s1*b.s0=b.s1*a.s0 then 0.5 else 0 end) y,
        sum(case when a.i1*b.i0>b.i1*a.i0 then 1 when a.i1*b.i0=b.i1*a.i0 then 0.5 else 0 end) z
    from endpoints a join endpoints b on a.s=b.s and a.r=b.r and a.span=b.span
    group by a.s,a.r,a.span,a.code
)
select s,r,span,count(*) n,round(corr(x,y),6) serpavi,round(corr(x,z),6) ipva
from ranks group by s,r,span order by span,s,r
