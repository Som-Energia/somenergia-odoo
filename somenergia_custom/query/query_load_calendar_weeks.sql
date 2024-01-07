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
			LPAD((EXTRACT('week' FROM day_of_year)::VARCHAR), 2, '0')
			as week_code
	from
	(select generate_series('2024-01-01'::DATE, '2050-12-31'::DATE, '1 day') AS day_of_year) sq_days_year
)sq_days_year
group by week_date, week_date_end, week_code, week_number, week_year, year
order by week_date, week_date_end, week_code, week_number, week_year, year;


delete from public.som_calendar_week
where id in (54,107,160,213,319,372,425,478,531,637,690,743,796,849,903,956,1009,1062,1115,1221,1274,1327,1380);

update public.som_calendar_week
set som_cw_week_number = 53, som_cw_code = 'W24_53', "name" = 'W24_53 [30/12/24 - 05/01/25]'
where id = 53;

update public.som_calendar_week
set som_cw_week_number = 53, som_cw_code = 'W25_53', "name" = 'W25_53 [29/12/25 - 04/01/26]'
where id = 106;

update public.som_calendar_week
set som_cw_week_number = 53, som_cw_code = 'W26_53', "name" = 'W26_53 [28/12/26 - 03/01/27]'
where id = 159;

update public.som_calendar_week
set som_cw_week_number = 53, som_cw_code = 'W29_53', "name" = 'W29_53 [31/12/29 - 06/01/30]'
where id = 318;

update public.som_calendar_week
set som_cw_week_number = 53, som_cw_code = 'W30_53', "name" = 'W30_53 [30/12/30 - 05/01/31]'
where id = 371;

update public.som_calendar_week
set som_cw_week_number = 53, som_cw_code = 'W31_53', "name" = 'W31_53 [29/12/31 - 04/01/32]'
where id = 424;

update public.som_calendar_week
set som_cw_week_number = 53, som_cw_code = 'W36_53', "name" = 'W36_53 [29/12/36 - 04/01/37]'
where id = 689;

update public.som_calendar_week
set som_cw_week_number = 53, som_cw_code = 'W40_53', "name" = 'W40_53 [31/12/40 - 06/01/41]'
where id = 902;

update public.som_calendar_week
set som_cw_week_number = 53, som_cw_code = 'W41_53', "name" = 'W41_53 [30/12/41 - 05/01/42]'
where id = 955;

update public.som_calendar_week
set som_cw_week_number = 53, som_cw_code = 'W46_53', "name" = 'W46_53 [31/12/46 - 06/01/47]'
where id = 1220;

update public.som_calendar_week
set som_cw_week_number = 53, som_cw_code = 'W47_53', "name" = 'W47_53 [30/12/47 - 05/01/48]'
where id = 1273;
