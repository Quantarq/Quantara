use soroban_sdk::panic_with_error;
use soroban_sdk::{contracterror, Env};

#[contracterror]
#[derive(Copy, Clone, Debug, Eq, PartialEq, PartialOrd, Ord)]
#[repr(u32)]
pub enum MathError {
    Overflow = 1,
    DivideByZero = 2,
}

pub trait SafeMathI128 {
    fn safe_add(self, env: &Env, other: i128) -> i128;
    fn safe_sub(self, env: &Env, other: i128) -> i128;
    fn safe_mul(self, env: &Env, other: i128) -> i128;
    fn safe_div(self, env: &Env, other: i128) -> i128;
}

impl SafeMathI128 for i128 {
    fn safe_add(self, env: &Env, other: i128) -> i128 {
        self.checked_add(other).unwrap_or_else(|| {
            panic_with_error!(env, MathError::Overflow);
        })
    }

    fn safe_sub(self, env: &Env, other: i128) -> i128 {
        self.checked_sub(other).unwrap_or_else(|| {
            panic_with_error!(env, MathError::Overflow);
        })
    }

    fn safe_mul(self, env: &Env, other: i128) -> i128 {
        self.checked_mul(other).unwrap_or_else(|| {
            panic_with_error!(env, MathError::Overflow);
        })
    }

    fn safe_div(self, env: &Env, other: i128) -> i128 {
        if other == 0 {
            panic_with_error!(env, MathError::DivideByZero);
        }
        self.checked_div(other).unwrap_or_else(|| {
            panic_with_error!(env, MathError::Overflow);
        })
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use proptest::prelude::*;
    use soroban_sdk::Env;

    proptest! {
        #![proptest_config(ProptestConfig::with_cases(1_000_000))]

        #[test]
        fn test_safe_add(a in any::<i128>(), b in any::<i128>()) {
            let env = Env::default();
            let result = std::panic::catch_unwind(|| {
                a.safe_add(&env, b)
            });

            match a.checked_add(b) {
                Some(expected) => {
                    assert_eq!(result.unwrap(), expected);
                }
                None => {
                    assert!(result.is_err());
                }
            }
        }

        #[test]
        fn test_safe_sub(a in any::<i128>(), b in any::<i128>()) {
            let env = Env::default();
            let result = std::panic::catch_unwind(|| {
                a.safe_sub(&env, b)
            });

            match a.checked_sub(b) {
                Some(expected) => {
                    assert_eq!(result.unwrap(), expected);
                }
                None => {
                    assert!(result.is_err());
                }
            }
        }

        #[test]
        fn test_safe_mul(a in any::<i128>(), b in any::<i128>()) {
            let env = Env::default();
            let result = std::panic::catch_unwind(|| {
                a.safe_mul(&env, b)
            });

            match a.checked_mul(b) {
                Some(expected) => {
                    assert_eq!(result.unwrap(), expected);
                }
                None => {
                    assert!(result.is_err());
                }
            }
        }

        #[test]
        fn test_safe_div(a in any::<i128>(), b in any::<i128>()) {
            let env = Env::default();
            let result = std::panic::catch_unwind(|| {
                a.safe_div(&env, b)
            });

            if b == 0 {
                assert!(result.is_err());
            } else {
                match a.checked_div(b) {
                    Some(expected) => {
                        assert_eq!(result.unwrap(), expected);
                    }
                    None => {
                        assert!(result.is_err());
                    }
                }
            }
        }
    }
}
