--This query gets the worked hours for one employee by weeks based on her attendances

select
	scw.id as week_id,
	scw.name as week_name,
	scw.som_cw_date as week_date,
	coalesce (sq_worked_hours.employee_id, %s) as employee_id,
	-1 * coalesce (sq_worked_hours.worked_hours, 0) as worked_hours
from som_calendar_week scw
left join
(
	SELECT
		employee_id,
		--min("hr_attendance_theoretical_time_report".id) AS id,
		--count("hr_attendance_theoretical_time_report".id) AS "__count" ,
		sum("hr_attendance_theoretical_time_report"."worked_hours") AS "worked_hours",
		--sum("hr_attendance_theoretical_time_report"."theoretical_hours") AS "theoretical_hours",
		--sum("hr_attendance_theoretical_time_report"."difference") AS "difference",
		date_trunc('week', "hr_attendance_theoretical_time_report"."date"::timestamp) as week_day
		--date_trunc('month', "hr_attendance_theoretical_time_report"."date"::timestamp) as "date:month"
	FROM "hr_attendance_theoretical_time_report"
	WHERE
		(
		("hr_attendance_theoretical_time_report"."employee_id" in (%s)) AND
		--(("hr_attendance_theoretical_time_report"."date" >= '2023-01-01') AND ("hr_attendance_theoretical_time_report"."date" <= '2023-02-28'))
		EXTRACT('year' FROM date) between 2024 and %s
		)
		AND TRUE
	GROUP BY
		employee_id,
		date_trunc('week', "hr_attendance_theoretical_time_report"."date"::timestamp)
		--date_trunc('month', "hr_attendance_theoretical_time_report"."date"::timestamp)
	ORDER BY employee_id,week_day --,"date:month"
)sq_worked_hours on scw.som_cw_date = sq_worked_hours.week_day
where scw.som_cw_year between 2024 and %s
