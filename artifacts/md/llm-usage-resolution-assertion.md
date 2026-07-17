# Claim Resolution: 

The thought: 
  Aim: To resolve as many claims as there are possible to resolve (max recall) this makes the downstream stages much more informed. 
  Stages: 
    1. Find the probable candidates fro resolution
      a. Is there any way we can boost the recall here by asking LLM with defined decision making and giving tools to travere the graph to figure oiut probably candidates. 
          How will we make 2 components aliases which have reported differnet names in claims, 
        what is a robust way of creating probable candidates.
        This is important since this is a gate for downstream 
    1. Use attributes , relationships, timestamp etc to figure out claims to merge. 
      1. Let's say we have all the probable candidates grouoed such that with this grouping we can certsinly resolve any 2 claims of they are same. 
      2. Do we need to empower an llm at any stage to make this better? obviously with decisive logic and haivng its response grounded in the knowledgfe graph itself. (and maybe any other source as given by the user)
    Doubt: 
      When finding probbale candidates for merging: lets say we get a set: A -> (B,C), B -> (A,C,D), E -> A : we need to make the resolution capable of disambiguating this whe group
      Post resolution lets say these candidates are merges and now if we see them as a collective claim can any other claim become a probbale candidate, I am asking this because this decides if this is a recursive proces ort one pass. 
    For candidates that are in the rejection pile or are in the HITL thresold pile, should we use an LLM to basically decide what to also downgrade some from HITL and/or raise soem from reject pile? for recall and accuracy. and also having prompt base fuzzy control over the HITL logic instead having to code it again and again based on feedback. 
    THe idea is that keeping the LLM output informed and having it make decisions taht we would code but with better control and maintainability. 
    Given we have all the probable candidates: 
    Are we certain that a function is eniugh to match them via atrtibutes relationships or do we need an llm for intelligent fuzziness match. 
  
    Is there any need to have an llm do a later pass to resolve orphans with information. 
    



# Assertion
  THe thought :
    This is most powerful when we already have resolved all claims possible for resolution.
    Similar abstract idea as above just for assertion purposes. 
    Here it is not about making the llm make the final decisoons but having it contribute in some scenarios ig.   