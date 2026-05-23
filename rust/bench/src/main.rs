use load_forecasting_blog_core::saidi_saifi_by_key;
use std::env;
use std::time::Instant;

fn main() {
    let n: usize = env::args().nth(1).and_then(|s| s.parse().ok()).unwrap_or(100_000);
    let iters: usize = env::args().nth(2).and_then(|s| s.parse().ok()).unwrap_or(5_000);
    let group_key: Vec<i64> = (0..n as i64).map(|i| i % 50).collect();
    let customers_out: Vec<f64> = (0..n).map(|i| (i % 7) as f64).collect();
    let slot_minutes: Vec<f64> = vec![15.0; n];
    let customers_served: Vec<f64> = vec![1000.0; n];
    let start = Instant::now();
    for _ in 0..iters {
        let _ = saidi_saifi_by_key(&group_key, &customers_out, &slot_minutes, &customers_served);
    }
    println!("elapsed: {:.3}s", start.elapsed().as_secs_f64());
}
