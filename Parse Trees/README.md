# Constituency Parse Trees

> Module: Intelligent Systems / Knowledge Representation  
> Date: 18 Sep 2025 (UTC+4)  
> Author: Abdullah Alshibli

---

## Overview
This document presents constituency-based (phrase-structure) parse trees for three sentences. Each tree follows a Penn Treebank-style bracket notation, and each build is shown step-by-step:  
1. Tokenisation & POS tagging  
2. Phrase grouping (NP/VP/PP)  
3. Full sentence tree  

For the ambiguous sentence, two alternative parses are provided.

**Legend:**  
- **S** = sentence  
- **NP** = noun phrase  
- **VP** = verb phrase  
- **PP** = prepositional phrase  
- **DT** = determiner  
- **NN/NNS** = noun(s)  
- **VBD/VBZ** = verb (past/3rd-person singular present)  
- **IN** = preposition  
- **.** = sentence-final period  

---

## 1) *The government raised interest rates.*

### Step A — Tokens & POS
```
The/DT government/NN raised/VBD interest/NN rates/NNS ./.
```

### Step B — Phrase chunks
- **NP (subject):** `(DT The) (NN government)`  
- **VP (predicate):** head verb **raised/VBD** + direct object NP `(NN interest) (NNS rates)`  

### Step C — Full constituency tree
```text
(S
  (NP (DT The) (NN government))
  (VP (VBD raised)
      (NP (NN interest) (NNS rates)))
  (. .))
```

---

## 2) *The internet gives everyone a voice.*

### Step A — Tokens & POS
```
The/DT internet/NN gives/VBZ everyone/NN a/DT voice/NN ./.
```

### Step B — Phrase chunks
- **NP (subject):** `(DT The) (NN internet)`  
- **VP (predicate):** head verb **gives/VBZ** (ditransitive)  
  - **NP (recipient):** `(NN everyone)`  
  - **NP (theme):** `(DT a) (NN voice)`  

### Step C — Full constituency tree
```text
(S
  (NP (DT The) (NN internet))
  (VP (VBZ gives)
      (NP (NN everyone))
      (NP (DT a) (NN voice)))
  (. .))
```

---

## 3) *The man saw the dog with the telescope.* (structural ambiguity)

### Step A — Tokens & POS
```
The/DT man/NN saw/VBD the/DT dog/NN with/IN the/DT telescope/NN ./.
```

### Step B/C — Two valid parses

**Interpretation A — PP attaches to VP**  
(instrumental reading: *the man used a telescope to see the dog*)  
```text
(S
  (NP (DT The) (NN man))
  (VP (VBD saw)
      (NP (DT the) (NN dog))
      (PP (IN with)
          (NP (DT the) (NN telescope))))
  (. .))
```

**Interpretation B — PP attaches to NP**  
(modifying *dog*: *the dog with the telescope*)  
```text
(S
  (NP (DT The) (NN man))
  (VP (VBD saw)
      (NP
        (NP (DT the) (NN dog))
        (PP (IN with)
            (NP (DT the) (NN telescope)))))
  (. .))
```

> Both trees are grammatically well-formed. The difference lies in attachment preference, which depends on semantics, prosody, or world knowledge.

---

## Learning Outcomes (Mapping)

- **LO1:** *“The knowledge and skills required to develop, deploy and evaluate the tools and techniques of intelligent systems to solve real-world problems.”*  
  **Evidence here:** applying NLP tools (tokenisation, POS tagging, phrase-structure building) and evaluating alternative parses for ambiguity.

- **LO2:** *“An understanding of contemporary research issues in the area of intelligent agent systems.”*  
  **Connection:** constituency parsing underpins agent communication/NLP pipelines (e.g., information extraction for agent reasoning). The attachment ambiguity illustrates challenges addressed by modern parsing research (probabilistic/Neural PCFGs, dependency vs. phrase-structure trade-offs).

---

## References
- Marcus, M. et al. (1993). *Building a large annotated corpus of English: The Penn Treebank.*  
- Jurafsky, D. & Martin, J. H. (2024). *Speech and Language Processing* (Chapter on Syntax & Parsing).

---

