#!/usr/bin/env node

/**
 * Claude Academic Skills - Local Discovery Tool
 * 用于在本地管理和发现已安装的学术技能
 */

const fs = require('fs');
const path = require('path');

const SKILLS_DIR = path.join(process.env.HOME || process.env.USERPROFILE, '.claude', 'skills', 'omc-learned');

function parseSkillMetadata(skillPath) {
  const skillMdPath = path.join(skillPath, 'SKILL.md');

  if (!fs.existsSync(skillMdPath)) {
    return null;
  }

  const content = fs.readFileSync(skillMdPath, 'utf-8');
  const yamlMatch = content.match(/^---\n([\s\S]*?)\n---/);

  if (!yamlMatch) {
    return null;
  }

  const yaml = yamlMatch[1];
  const metadata = {};

  // Parse YAML frontmatter
  yaml.split('\n').forEach(line => {
    const [key, ...valueParts] = line.split(':');
    if (key && valueParts.length > 0) {
      const value = valueParts.join(':').trim();

      if (key.trim() === 'triggers') {
        // Handle array format
        metadata.triggers = [];
      } else if (key.trim().startsWith('  -')) {
        // Array item
        if (metadata.triggers) {
          metadata.triggers.push(value.replace(/^['"]|['"]$/g, ''));
        }
      } else {
        metadata[key.trim()] = value.replace(/^['"]|['"]$/g, '');
      }
    }
  });

  return metadata;
}

function listSkills() {
  if (!fs.existsSync(SKILLS_DIR)) {
    console.log('❌ Skills directory not found:', SKILLS_DIR);
    return;
  }

  const skills = fs.readdirSync(SKILLS_DIR)
    .filter(f => fs.statSync(path.join(SKILLS_DIR, f)).isDirectory())
    .map(skillName => {
      const skillPath = path.join(SKILLS_DIR, skillName);
      const metadata = parseSkillMetadata(skillPath);
      return { name: skillName, ...metadata };
    })
    .filter(s => s.name);

  if (skills.length === 0) {
    console.log('❌ No skills found');
    return;
  }

  console.log('\n📚 Academic Skills Installed:\n');
  console.log('┌─────────────────────────────────────────────────────────────┐');

  skills.forEach((skill, idx) => {
    console.log(`│ ${idx + 1}. ${skill.name}`);
    if (skill.description) {
      console.log(`│    📝 ${skill.description}`);
    }
    if (skill.triggers && skill.triggers.length > 0) {
      console.log(`│    🔑 Triggers: ${skill.triggers.slice(0, 3).join(', ')}${skill.triggers.length > 3 ? '...' : ''}`);
    }
    console.log('│');
  });

  console.log('└─────────────────────────────────────────────────────────────┘');
  console.log(`\n✅ Total: ${skills.length} skills installed\n`);
}

function searchSkills(query) {
  if (!fs.existsSync(SKILLS_DIR)) {
    console.log('❌ Skills directory not found');
    return;
  }

  const skills = fs.readdirSync(SKILLS_DIR)
    .filter(f => fs.statSync(path.join(SKILLS_DIR, f)).isDirectory())
    .map(skillName => {
      const skillPath = path.join(SKILLS_DIR, skillName);
      const metadata = parseSkillMetadata(skillPath);
      return { name: skillName, ...metadata };
    })
    .filter(s => s.name);

  const results = skills.filter(skill => {
    const searchStr = `${skill.name} ${skill.description || ''} ${(skill.triggers || []).join(' ')}`.toLowerCase();
    return searchStr.includes(query.toLowerCase());
  });

  if (results.length === 0) {
    console.log(`\n❌ No skills found matching: "${query}"\n`);
    return;
  }

  console.log(`\n🔍 Found ${results.length} skill(s) matching "${query}":\n`);
  results.forEach(skill => {
    console.log(`✓ ${skill.name}`);
    if (skill.description) {
      console.log(`  ${skill.description}`);
    }
    if (skill.triggers && skill.triggers.length > 0) {
      console.log(`  Triggers: ${skill.triggers.join(', ')}`);
    }
    console.log();
  });
}

function showHelp() {
  console.log(`
Claude Academic Skills - Local Discovery Tool

Usage:
  skills list              List all installed skills
  skills search <query>    Search for a skill
  skills help              Show this help message

Examples:
  skills list
  skills search ppt
  skills search literature
  `);
}

// Main
const command = process.argv[2];
const arg = process.argv[3];

switch (command) {
  case 'list':
    listSkills();
    break;
  case 'search':
    if (!arg) {
      console.log('❌ Please provide a search query');
      showHelp();
    } else {
      searchSkills(arg);
    }
    break;
  case 'help':
  case '--help':
  case '-h':
    showHelp();
    break;
  default:
    listSkills();
}
