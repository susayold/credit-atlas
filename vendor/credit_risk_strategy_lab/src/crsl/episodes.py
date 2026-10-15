"""Forward-only D3 episode events; sustained cure known only on third current month."""
def episode_events(rows):
    """Rows sorted by (loan_id, period): loan_id, date, state, terminal_type.

    Unknown or a gap breaks episode linkage. First-ever observed D3 never resets.
    No treatment-effect inference. The caller must validate unique monthly grain.
    """
    loan=None; previous=None; ever=False; open_episode=False; cured=False; streak=0
    for loan_id,period,state,terminal in rows:
        if loan_id!=loan:
            loan=loan_id; previous=None; ever=False; open_episode=False; cured=False; streak=0
        if previous is not None:
            diff=(period.year-previous.year)*12+period.month-previous.month
            if diff<=0: raise ValueError('Episode dates must be strictly increasing per loan')
            if diff!=1: open_episode=False; cured=False; streak=0
        previous=period
        if terminal is not None and state!='D3PLUS':
            open_episode=False; cured=False; streak=0
            continue
        if state=='UNKNOWN':
            open_episode=False; cured=False; streak=0
        elif state=='D3PLUS':
            if not ever:
                yield loan_id,period,'FIRST_OBSERVED_D3'
            elif cured:
                yield loan_id,period,'REDEFAULT_AFTER_SUSTAINED_CURE'
            ever=True; open_episode=True; cured=False; streak=0
        elif state=='CURRENT' and open_episode:
            streak+=1
            if streak==1: yield loan_id,period,'ONE_MONTH_CURE'
            if streak==3:
                yield loan_id,period,'SUSTAINED_CURE_CONFIRMED'
                cured=True; open_episode=False
        else:
            streak=0
        if terminal is not None:
            open_episode=False; cured=False; streak=0
