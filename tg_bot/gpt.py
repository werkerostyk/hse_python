import torch
from transformers import AutoModelWithLMHead, AutoTokenizer


def conversation(text):
    # logging.set_verbosity_error()
    device = 'cuda' if torch.cuda.is_available() else 'cpu'
    tokenizer = AutoTokenizer.from_pretrained('sberbank-ai/rugpt3large_based_on_gpt2')
    model = AutoModelWithLMHead.from_pretrained('sberbank-ai/rugpt3large_based_on_gpt2').to(device)
    model.eval()

    # text = 'Ты - бот погоды, которому могут задавать вопросы\nСообщение: '
    # text += 'Как дела, бот?' + '\n'
    # text = text + 'Ответ: '
    print(text)
    tokens = tokenizer.encode(text, return_tensors='pt').to(device)
    # UnboundLocalError: local variable 'next_tokens' referenced before assignment
    # хотя max_length каждый раз должен быть новым
    prediction = model.generate(tokens, len(text.split()) + 50, do_sample=True, num_beams=7, temperature=0.6, top_k=5, top_p=0.95)
    ans = tokenizer.decode(prediction[0])
    print(ans)
    return ans[ans.rfind('Ответ: ')+7:].strip()
