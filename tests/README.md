# Using the TextGenerator Agent

## Step 1. Generate Text for your questions

The TextGenerator Agent is a text generator that will simulate the scope of a proposal that 
each question in the CARE Worksheet intends to ask.  It operates on a per Agent loop like the 
regular Agent that is used to evaluate proposals. The first step in the process is to use the
provided `make_data.py` script. The only other options are the path to the CARE file (`-c --care_file`), 
the directory to output the synthetic data into (`-o --out_dir`), and a new parameter: `-i --id`.
This new parameter is the name of a column header that represents a unique identifier for each
question.  It will be used later to test the effectiveness of retrieval. As with the regular 
Agent parsing, this process can take a couple of hours depending on the model. The output will be
a set of `txt` files corresponding to each agent (`e.g. System Engineer, Ethicist, etc.`). 
Inside each of these documents are text passages that answer the questions provided in the 
associated CARE file - effectively serving as a positive control, with a twist.  The twist
is that each answer is tagged with the unique identifier for the question used to derive 
the text.

```shell
python make_data.py --care_file resources/AgentQuestions.xlsm --id 'TRL.Track.Step.Item'
```

## Step 2. Generate corpora
Now that we have all agents with all questions answered, we can create multiple reports, each 
with different levels of completion.  For example, if we include all outputs, then the report 
generated by the CARE agent framework, should indicate that all questions were answered. Moreover,
we can verify the retrieval process was effective - regardless if the binary agent attested a
negative finding. In this way, we can separate out the fault of the retriever and the fault of
the LLM.

For simplicity, we will generate four datasets: 

1. Complete: All synthetic text
2. EarlyComplete: Exclude Governance body, since all but 1 task is TRL7-9
3. NoCISME: Exclude Clinical Informatics SME, since they contribute 20% of the work mostly TRL4-5.
4. StopAt7: Remove all TRL 8-9 from all Agents

However, we will also need to do a little preprocessing as well.
```shell
cd synthetics
find . \( -name "*txt" ! -name "EarlyComplete.txt" ! -name "NoCISME.txt" ! -name "Complete.txt" \) -type f -exec cat {} + > Complete.txt
find . \( -name "*txt" ! -name "governance_body.txt" ! -name "EarlyComplete.txt" ! -name "NoCISME.txt" ! -name "Complete.txt" \) -type f -exec cat {} + > EarlyComplete.txt
find . \( -name "*txt" ! -name "clinical_informatics_sme.txt" ! -name "EarlyComplete.txt" ! -name "NoCISME.txt" ! -name "Complete.txt" \) -type f -exec cat {} + > NoCISME.txt
cd ..
#python utils/test_cleaner.py -i synthetics/Complete.txt -o synthetics/CompleteClean.txt
#python utils/test_cleaner.py -i synthetics/EarlyComplete.txt -o synthetics/EarlyCompleteClean.txt
#python utils/test_cleaner.py -i synthetics/NoCISME.txt -o synthetics/NoCISMEClean.txt
#python utils/test_cleaner.py -i synthetics/Complete.txt -o synthetics/StopAt7Clean.txt -e
```

## Step 3. Look at performance of different chunking strategies
```shell
python main.py -p synthetics/Complete.txt -o synthetics/Complete.semantic -C semantic
python main.py -p synthetics/Complete.txt -o synthetics/Complete.char     -C character
python main.py -p synthetics/Complete.txt -o synthetics/Complete.recur    -C recursive
````

## Step 4. Evaluate corpora
Now we need to run the generated text files through the CARE Agent.
```shell
python main.py -p synthetics/Complete.txt -o synthetics/Complete.
#python main.py -p synthetics/EarlyComplete.txt -o synthetics/EarlyComplete
#python main.py -p synthetics/NoCISME.txt -o synthetics/NoCISME
#python main.py -p synthetics/StopAt7Clean.txt -o synthetics/StopAt7Clean
```

# Step 5. Assess performance
