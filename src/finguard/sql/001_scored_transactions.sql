-- 거래와 당시 응답을 한 행에 저장해 둘 중 하나만 남는 일을 막는다.
CREATE TABLE IF NOT EXISTS scored_transactions (
    sequence bigint GENERATED ALWAYS AS IDENTITY UNIQUE,
    transaction_id text PRIMARY KEY CHECK (length(transaction_id) > 0),
    card_id text NOT NULL CHECK (length(card_id) > 0),
    occurred_at timestamp without time zone NOT NULL,
    amount numeric NOT NULL CHECK (amount > 0 AND scale(amount) <= 2),
    category text NOT NULL CHECK (length(category) > 0),
    result jsonb NOT NULL CHECK (jsonb_typeof(result) = 'object'),
    created_at timestamp with time zone NOT NULL DEFAULT current_timestamp
);

-- 같은 시각 거래는 서버가 확정한 순서를 따른다.
CREATE INDEX IF NOT EXISTS scored_transactions_card_time
    ON scored_transactions (card_id, occurred_at, sequence);
