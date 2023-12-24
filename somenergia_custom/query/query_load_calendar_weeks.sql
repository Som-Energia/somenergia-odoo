--delete from som_calendar_week;
--DROP TABLE public.som_calendar_week;

insert into som_calendar_week (
    name,
    som_cw_code,
    som_cw_date,
    som_cw_date_end,
    som_cw_week_number,
    som_cw_week_year,
    som_cw_year)
select
	week_code::VARCHAR || ' [' || TO_CHAR(week_date, 'DD/MM/YY') || ' - ' || TO_CHAR(week_date_end, 'DD/MM/YY') || ']' as name,
	week_code,
	week_date,
	week_date_end,
	week_number,
	week_year,
	year
from
(
	select
		sq_days_year.day_of_year,
		date_trunc('week', day_of_year::timestamp) as week_date ,
		date_trunc('week', day_of_year::timestamp) + interval '6 days' as week_date_end,
		EXTRACT('week' FROM day_of_year) AS week_number,
		EXTRACT('year' FROM (date_trunc('week', day_of_year::timestamp))) AS week_year,
		EXTRACT('year' FROM day_of_year) AS year,
		'W'::VARCHAR ||
			RIGHT(EXTRACT('year' FROM (date_trunc('week', day_of_year::timestamp)))::VARCHAR,2) || '_' ||
			EXTRACT('week' FROM day_of_year)::VARCHAR
			as week_code
	from
	(select generate_series('2023-01-01'::DATE, '2050-12-31'::DATE, '1 day') AS day_of_year) sq_days_year
)sq_days_year
group by week_date, week_date_end, week_code, week_number, week_year, year
order by week_date, week_date_end, week_code, week_number, week_year, year;


update public.som_calendar_week
set som_cw_code = 'W24_53', "name" = 'W24_53 [30/12/24 - 05/01/25]'
where id = 106;

update public.som_calendar_week
set som_cw_code = 'W25_1', "name" = 'W25_1 [30/12/24 - 05/01/25]'
where id = 107;

update public.som_calendar_week
set som_cw_code = 'W25_53', "name" = 'W25_53 [29/12/25 - 04/01/26]'
where id = 159;

update public.som_calendar_week
set som_cw_code = 'W2026_1', "name" = 'W26_1 [29/12/25 - 04/01/26]'
where id = 160;

