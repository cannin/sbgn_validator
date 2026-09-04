use sbgn_validator::{NamespacePolicy, Validator, rules};
use std::path::Path;

fn main() -> Result<(), Box<dyn std::error::Error>> {
    let args: Vec<String> = std::env::args().skip(1).collect();
    let mut schema = None;
    let mut document = None;
    let mut phase = "basic".to_owned();
    let mut include_backend = false;
    let mut allow_sbgnml_0_2 = false;
    let mut show_rules_info = false;
    let mut positional = Vec::new();
    let mut index = 0;
    while index < args.len() {
        match args[index].as_str() {
            "--backend" => {
                include_backend = true;
                index += 1;
            }
            "--allow-sbgnml-0.2" => {
                allow_sbgnml_0_2 = true;
                index += 1;
            }
            "--rules-info" => {
                show_rules_info = true;
                index += 1;
            }
            "--schema" | "--document" | "--phase" => {
                if index + 1 >= args.len() {
                    return Err(format!("missing value for {}", args[index]).into());
                }
                match args[index].as_str() {
                    "--schema" => schema = Some(args[index + 1].clone()),
                    "--document" => document = Some(args[index + 1].clone()),
                    "--phase" => phase = args[index + 1].clone(),
                    _ => unreachable!(),
                }
                index += 2;
            }
            option if option.starts_with("--") => {
                return Err(format!("unknown option: {option}\n{}", usage()).into());
            }
            value => {
                positional.push(value.to_owned());
                index += 1;
            }
        }
    }
    if show_rules_info {
        println!("{}", serde_json::to_string_pretty(&rules::rules_info()?)?);
        return Ok(());
    }
    if document.is_none() && positional.len() == 1 {
        document = positional.pop();
    }
    if !positional.is_empty() {
        return Err(usage().into());
    }
    let document = document.ok_or_else(usage)?;
    let namespace_policy = if allow_sbgnml_0_2 {
        NamespacePolicy::AllowSbgnml02
    } else {
        NamespacePolicy::Strict03
    };
    let validator = match schema {
        Some(schema) => Validator::compile_for_document(
            Path::new(&schema),
            Path::new(&document),
            &phase,
            namespace_policy,
        )?,
        None => Validator::builtin_for_document_with_policy(
            Path::new(&document),
            &phase,
            namespace_policy,
        )?,
    };
    let mut report = validator.validate(Path::new(&document))?;
    if !include_backend {
        report = report.without_backend();
    }
    println!("{}", serde_json::to_string_pretty(&report)?);
    Ok(())
}

fn usage() -> String {
    "usage: sbgn-validator DOCUMENT [--schema PATH] [--phase NAME] [--backend] \
     [--allow-sbgnml-0.2]"
        .to_owned()
}
