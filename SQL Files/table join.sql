---Query to check rows 

select
  count(*) as crm_rows,
  countif(c.call_id is null) as crm_rows_with_no_call,
  (select count(*) from `customer-call-data.silver_calls.silver-calls`) as call_rows
from `customer-call-data.crm_data.crm_data` as m
left join `customer-call-data.silver_calls.silver-calls` as c
  on m.call_id = c.call_id;


---Agent Coversion rates 

select
  c.agent_id,
  count(*) as calls,
  countif(m.disposition = 'sale') as sales,
  round(safe_divide(countif(m.disposition = 'sale'), count(*)) * 100, 1) as conversion_pct,
  round(sum(m.order_value_gbp), 2) as revenue_gbp
from `customer-call-data.silver_calls.silver-calls` as c
join `customer-call-data.crm_data.crm_data` as m
  on c.call_id = m.call_id
group by c.agent_id
order by conversion_pct desc;

---Create combined view of CRM table and call logs

create or replace view `customer-call-data.silver_calls.calls_joined` as
select
  c.call_id,
  c.source_file,
  c.agent_id,
  c.campaign,
  c.direction,
  c.start_time,
  c.end_time,
  c.duration_seconds,
  c.queue_wait_seconds,
  c.engine_confidence,
  c.language,
  c.n_turns,
  c.overall_sentiment,
  c.sentiment_score,
  c.customer_intent,
  c.topics,
  c.cancellation_rights_read,
  c.exit_fee_disclosed,
  c.call_recording_notice_given,
  c.talk_ratio_agent,
  c.silence_seconds,
  c.agent_assist_prompts_shown,
  -- outcome columns come from the crm table, the source of truth for sales
  m.disposition,
  m.product_sold,
  m.contract_months,
  m.order_value_gbp,
  -- a few helper columns so the gold queries stay short
  m.disposition = 'sale' as is_sale,
  (c.cancellation_rights_read
    and c.exit_fee_disclosed
    and c.call_recording_notice_given) as all_compliance_checks_passed,
  extract(hour from c.start_time) as call_hour
from `customer-call-data.silver_calls.silver-calls` as c
left join `customer-call-data.crm_data.crm_data` as m
  on c.call_id = m.call_id;