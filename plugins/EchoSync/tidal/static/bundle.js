var e = 1024, t = 2048, n = 4096, r = 8192, i = 32768, a = 1 << 25, o = 65536, s = 1 << 19, c = 1 << 20, l = 1 << 25, u = 1 << 21, d = 1 << 22, f = 1 << 23, p = 1 << 27, m = 1 << 26, h = Symbol("$state"), g = Symbol("component"), _ = Symbol("legacy props"), v = Symbol(""), y = Symbol("attributes"), b = Symbol("class"), x = Symbol("style"), S = Symbol("text"), C = Symbol("form reset"), w = new class extends Error {
	name = "StaleReactionError";
	message = "The reaction that called `getAbortSignal()` was re-run or destroyed";
}(), ee = !!globalThis.document?.contentType && /* @__PURE__ */ globalThis.document.contentType.includes("xml"), T = {}, E = Symbol("uninitialized");
function te() {
	console.warn("https://svelte.dev/e/derived_inert");
}
function ne(e) {
	console.warn("https://svelte.dev/e/hydration_mismatch");
}
function re() {
	console.warn("https://svelte.dev/e/svelte_boundary_reset_noop");
}
// node_modules/svelte/src/internal/client/dom/hydration.js
var D = !1;
function ie(e) {
	D = e;
}
var O;
function k(e) {
	if (e === null) throw ne(), T;
	return O = e;
}
function ae() {
	return k(/* @__PURE__ */ Fr(O));
}
function A(e) {
	if (D) {
		if (/* @__PURE__ */ Fr(O) !== null) throw ne(), T;
		O = e;
	}
}
function oe(e = 1) {
	if (D) {
		for (var t = e, n = O; t--;) n = /* @__PURE__ */ Fr(n);
		O = n;
	}
}
function se(e = !0) {
	for (var t = 0, n = O;;) {
		if (Gr(n) === 8) {
			var r = ni(n) ?? "";
			if (r === "]") {
				if (t === 0) return n;
				--t;
			} else (r === "[" || r === "[!" || r.startsWith("[?") || r[0] === "[" && !isNaN(Number(r.slice(1)))) && (t += 1);
		}
		var i = /* @__PURE__ */ Fr(n);
		e && Qr(n), n = i;
	}
}
function ce(e) {
	if (!e || Gr(e) !== 8) throw ne(), T;
	return ni(e) ?? "";
}
// node_modules/svelte/src/internal/shared/utils.js
var le = Array.isArray, ue = Array.prototype.indexOf, de = Array.prototype.includes, fe = Array.from, pe = Object.keys, me = Object.defineProperty, he = Object.getOwnPropertyDescriptor, ge = Object.getOwnPropertyDescriptors, _e = Object.prototype, ve = Array.prototype, ye = Object.getPrototypeOf, be = Object.isExtensible, xe = () => {};
function Se(e) {
	return e();
}
function Ce(e) {
	for (var t = 0; t < e.length; t++) e[t]();
}
function we() {
	var e, t;
	return {
		promise: new Promise((n, r) => {
			e = n, t = r;
		}),
		resolve: e,
		reject: t
	};
}
function Te(e) {
	var t = W;
	if (t === null) return e;
	if (!(t.f & 32768) && !(t.f & 4)) throw e;
	Ee(e, t);
}
function Ee(e, t) {
	if (e === T) throw e;
	if (!(t !== null && t.f & 16384)) {
		for (; t !== null;) {
			if (t.f & 128 && !(t.f & 33570816)) {
				if (!(t.f & 32768)) throw e;
				try {
					t.b.error(e);
					return;
				} catch (t) {
					e = t;
				}
			}
			t = t.parent;
		}
		throw e;
	}
}
function De(e) {
	throw Error("https://svelte.dev/e/lifecycle_outside_component");
}
function Oe(e, t, n) {
	throw Error("https://svelte.dev/e/each_key_duplicate");
}
function ke(e) {
	throw Error("https://svelte.dev/e/effect_in_teardown");
}
function Ae() {
	throw Error("https://svelte.dev/e/effect_in_unowned_derived");
}
function je(e) {
	throw Error("https://svelte.dev/e/effect_orphan");
}
function Me() {
	throw Error("https://svelte.dev/e/effect_update_depth_exceeded");
}
function Ne() {
	throw Error("https://svelte.dev/e/hydration_failed");
}
function Pe(e) {
	throw Error("https://svelte.dev/e/props_invalid_value");
}
function Fe() {
	throw Error("https://svelte.dev/e/state_descriptors_fixed");
}
function Ie() {
	throw Error("https://svelte.dev/e/state_prototype_fixed");
}
function Le() {
	throw Error("https://svelte.dev/e/state_unsafe_mutation");
}
function Re() {
	throw Error("https://svelte.dev/e/svelte_boundary_reset_onerror");
}
// node_modules/svelte/src/internal/flags/index.js
var ze = !1;
function Be() {
	ze = !0;
}
// node_modules/svelte/src/internal/client/context.js
var j = null;
function Ve(e) {
	j = e;
}
function He(e, t = !1, n) {
	j = {
		p: j,
		i: !1,
		c: null,
		e: null,
		s: e,
		x: null,
		r: W,
		l: ze && !t ? {
			s: null,
			u: null,
			$: []
		} : null
	};
}
function Ue(e) {
	var t = j, n = t.e;
	if (n !== null) {
		t.e = null;
		for (var r of n) cn(r);
	}
	return e !== void 0 && (t.x = e), t.i = !0, j = t.p, We(e);
}
function We(e = {}) {
	return me(e, g, { value: !0 }), e;
}
function Ge() {
	return !ze || j !== null && j.l === null;
}
// node_modules/svelte/src/internal/client/dom/task.js
var Ke = [];
function qe() {
	var e = Ke;
	Ke = [], Ce(e);
}
function Je(e) {
	if (Ke.length === 0 && !It) {
		var t = Ke;
		queueMicrotask(() => {
			t === Ke && qe();
		});
	}
	Ke.push(e);
}
function Ye() {
	for (; Ke.length > 0;) qe();
}
// node_modules/svelte/src/internal/client/reactivity/equality.js
function Xe(e) {
	return e === this.v;
}
function Ze(e, t) {
	return e == e ? e !== t || typeof e == "object" && !!e || typeof e == "function" : t == t;
}
function Qe(e) {
	return !Ze(e, this.v);
}
// node_modules/svelte/src/internal/client/custom-renderer/state.js
var $e = null;
// node_modules/svelte/src/internal/client/reactivity/async.js
function et(e, t, n, r) {
	var i = W, a = t.map(Ge() ? st : dt), s = e.filter((e) => !e.settled);
	if (s.length > 0) {
		var c = tt(), l = it();
		(s.length === 1 ? s[0].promise : Promise.all(s.map((e) => e.promise))).then(() => {
			if (!(i.f & 16384)) {
				c(s[0].run.get_batch());
				try {
					u();
				} catch (e) {
					Ee(e, i);
				}
				nt();
			}
		}).finally(l);
	} else u();
	function u() {
		if (!e.some((e) => e.failed)) {
			if (n.length === 0) r(a);
			else {
				var t = n.map((e) => /* @__PURE__ */ lt(e)), s = null;
				gn(() => {
					for (var e of t) if (ut(e)) {
						Y(e);
						return;
					}
					s === null ? s = B(() => {
						try {
							r([...a, ...t]);
						} catch (e) {
							Ee(e, i);
						}
					}) : I.revalidate_branch(s);
				}, o);
			}
		}
	}
}
function tt() {
	var e = W, t = H, n = j, r = I;
	return function(i = r) {
		Ln(e), U(t), Ve(n), i !== null && !(e.f & 16384) && M(i).activate();
	};
}
function nt(e = !0) {
	Ln(null), U(null), Ve(null), e && I?.deactivate();
}
var rt = null;
function it() {
	for (var e = W, t = e.b, n = M(I), r = t; r && !r.is_pending;) r = r.parent;
	return n.increment(e), r?.increment(e, n), t?.update_effect_pending(1), () => {
		M(n).decrement(e), r?.decrement(e, n), t?.update_effect_pending(-1);
	};
}
function M(e) {
	for (; e.merged !== null;) e = e.merged;
	return e;
}
// node_modules/svelte/src/internal/client/reactivity/status.js
var at = ~(t | n | e);
function N(e, t) {
	e.f = e.f & at | t;
}
function ot(t) {
	t.f & 512 || t.edges === null ? N(t, e) : N(t, n);
}
/*#__NO_SIDE_EFFECTS__*/
function st(e) {
	var n = 2 | t;
	return W !== null && (W.f |= s), {
		ctx: j,
		deps: null,
		dv: null,
		edges: null,
		effects: null,
		equals: Xe,
		f: n,
		fn: e,
		reactions: null,
		rv: 0,
		v: E,
		wv: 0,
		parent: W,
		ac: null
	};
}
var ct = Symbol("obsolete");
/*#__NO_SIDE_EFFECTS__*/
function lt(e, t, n, r) {
	var i = bt(E);
	i.f |= d;
	var a = /* @__PURE__ */ new Set(), o = rt, s = o && I, c = o && [];
	function l(e = !1) {
		var t = c;
		c = e ? null : [], e && (s = null);
		for (let e of t) e();
	}
	return pn(() => {
		var t = W, n = we();
		try {
			var u = e();
			if (u === E) return;
			var d = Promise.resolve(u), f = J?.signal;
			d.then((e) => {
				f?.aborted || n.resolve(e);
			}, (e) => {
				f?.aborted || e === w && o === null || n.reject(e === w ? ct : e);
			}).finally(nt);
		} catch (e) {
			n.reject(e);
		}
		var p = I, m = it();
		p.async_deriveds.get(t)?.reject(ct), a.add(n), p.async_deriveds.set(t, n);
		let h = (e, u = void 0) => {
			if (c !== null && u !== ct && (s ??= p, M(p) !== M(s))) c.push(() => {
				var r = !!(t.f & 16384) || (p.linked ? p.async_deriveds.get(t) !== n : !M(p).linked);
				h(e, r ? ct : u);
			});
			else {
				if (m(), a.delete(n), u) {
					if (c !== null && s !== null && (a.size > 0 || u === ct) && M(s) === M(p) && M(p).async_deriveds.get(t) === n) {
						s = null, l();
						return;
					}
					if (u === ct) return;
				}
				var d = i.equals(e) && !u && !(i.f & 8388608);
				M(p).capture(i, u ?? e, d, !!u), o !== null && (o.switch(p), o.continued.push(() => l(!0)), o = null), r?.(u), r = void 0;
			}
		};
		n.promise.then(h, (e) => h(null, e || "unknown"));
	}), on(() => {
		for (let e of a) e.reject(ct);
	}), i;
}
function ut(e) {
	return (R?.get(e) ?? e).v === E;
}
/*#__NO_SIDE_EFFECTS__*/
function dt(e) {
	let t = /* @__PURE__ */ st(e);
	return t.equals = Qe, t;
}
function ft(e) {
	var t = e.effects;
	if (t !== null) {
		e.effects = null;
		for (var n = 0; n < t.length; n += 1) V(t[n]);
	}
}
function pt(e) {
	var t = W, n = e.parent;
	if (!Mn && n !== null && e.v !== E && n.f & 24576) return te(), ot(e), e.v;
	Ln(n);
	try {
		return ft(e), or(e);
	} finally {
		Ln(t);
	}
}
function mt(e) {
	var t = e;
	if (Xn(t)) {
		var n = z?.records, r = n?.get(t);
		r !== void 0 && qn(r.deps, r.dv) ? (n.delete(t), pr(t, r)) : pt(t);
	}
}
function ht(e) {
	var t = Nt, n = t.get(e);
	if (n !== void 0) return n;
	var r = z, i = R.get(e), a = i ?? e, o = i === void 0 ? (e.f & m) !== 0 : i.assigned, s = r.get_record(e);
	return o && !Jn((s ?? e).deps, a.wv) ? n = a : s !== void 0 && qn(s.deps, s.dv) ? n = s : i === void 0 && !o && e.dv !== null && qn(e.deps, e.dv) ? n = e : (pt(e), n = r.records?.get(e) ?? e), e.f & 512 && t.set(e, n), n;
}
function gt(e) {
	if (e.effects !== null) for (let t of e.effects) (t.teardown || t.f & 134217728) && (t.teardown?.(), ir(t), t.fn !== null && (t.teardown = xe), vr(t), vn(t));
}
function _t(e) {
	if (e.effects !== null) for (let t of e.effects) t.teardown && t.fn !== null && yr(t);
}
// node_modules/svelte/src/internal/client/reactivity/sources.js
var vt = /* @__PURE__ */ new Set(), yt = !1;
function bt(e, t) {
	return {
		f: 0,
		v: e,
		reactions: null,
		equals: Xe,
		rv: 0,
		wv: 0
	};
}
/*#__NO_SIDE_EFFECTS__*/
function xt(e, t) {
	let n = bt(e, t);
	return zn(n), n;
}
/*#__NO_SIDE_EFFECTS__*/
function St(e, t = !1, n = !0) {
	let r = bt(e);
	return t || (r.equals = Qe), ze && n && j !== null && j.l !== null && (j.l.s ??= []).push(r), r;
}
function Ct(e, t) {
	return P(e, X(() => Y(e))), t;
}
function P(e, t, n = !1) {
	return H !== null && (!In || H.f & 131072) && Ge() && H.f & 4325394 && (Rn === null || !Rn.has(e)) && Le(), wt(e, n ? Dr(t) : t, Rt);
}
function wt(e, t, n = null) {
	var r = e.equals(t) && !(e.f & 8388608), i = R?.get(e);
	if (!r || i !== void 0 && (i.e || !e.equals.call(i, t))) {
		var a = Wt.ensure();
		(e.f & 67110914) == 2050 && pt(e), a.capture(e, t, r, !1, n), Ge() && W !== null && W.f & 1024 && !(W.f & 96) && (q === null ? Bn([e]) : q.push(e));
	} else Mn && Mt(e);
	return t;
}
function Tt() {
	yt = !1, $t(Et);
}
function Et() {
	for (let e of vt) {
		e.f & 1024 && N(e, n);
		let t;
		try {
			t = Xn(e);
		} catch {
			t = !0;
		}
		t && yr(e);
	}
	vt.clear();
}
function Dt(e) {
	P(e, e.v + 1);
}
// node_modules/svelte/src/internal/client/reactivity/batch.js
var F = null, Ot = null, I = null, kt = null, L = null;
function At(e) {
	L = e;
}
function jt(e) {
	var t = L = {
		reverted_values: new Map(L?.reverted_values),
		derived_cache: /* @__PURE__ */ new Map(),
		parent: L
	};
	for (let [n, r] of e ?? []) t.reverted_values.set(n, r);
	return t;
}
function Mt(e) {
	for (var t = L; t !== null; t = t.parent) t.reverted_values.delete(e), t.derived_cache.clear();
}
var R = null, Nt = null, z = null, Pt = null, Ft = /* @__PURE__ */ new Set(), It = !1, Lt = null, Rt = null, zt = 0, Bt = null, Vt = 0, Ht = 1, Ut = null, Wt = class r {
	id = Ht++;
	started = !1;
	linked = !0;
	prev = null;
	next = null;
	async_deriveds = /* @__PURE__ */ new Map();
	current = /* @__PURE__ */ new Map();
	previous = /* @__PURE__ */ new Map();
	records = null;
	folded = [];
	#e = /* @__PURE__ */ new Map();
	#t = /* @__PURE__ */ new Map();
	#n = /* @__PURE__ */ new Map();
	#r = null;
	#i = /* @__PURE__ */ new Map();
	#a = [];
	#o = /* @__PURE__ */ new Set();
	#s = /* @__PURE__ */ new Set();
	is_fork = !1;
	merged = null;
	merge_requests = /* @__PURE__ */ new Set();
	#c = !1;
	constructor() {
		Ot === null ? F = Ot = this : (Ot.next = this, this.prev = Ot), Ot = this;
	}
	#l() {
		if (this.is_fork) return !0;
		for (let e of this.#n.keys()) if (this.is_blocked_by(e)) return !0;
		return !1;
	}
	#u(e) {
		return this.#o.has(e) || !!(e.f & 33554432) && !this.#s.has(e);
	}
	is_skipped(e) {
		for (var t = e; t !== null; t = t.parent) if (this.#u(t)) return !0;
		return !1;
	}
	is_blocked_by(e, t = null) {
		for (var n = e; n !== null && n !== t; n = n.parent) if (this.#u(n) || (n.f & 16512) == 128 && n.b.is_pending) return !1;
		return !0;
	}
	skip_effect(e) {
		this.#o.add(e), this.#s.delete(e);
	}
	unskip_effect(e) {
		(this.#o.delete(e) || !this.#s.has(e) && (e.f & 33554432 || this.folded.some((t) => t.#o.has(e)))) && this.revalidate_branch(e), this.#s.add(e);
	}
	unskip_new_effect(e) {
		this.#s.add(e);
	}
	revalidate_branch(e) {
		for (var t = e.first; t !== null; t = t.next) {
			var r = t.f;
			!(r & 24576) && !this.#u(t) && (!(r & 131168) && t.fn !== null && this.schedule(t, n), this.revalidate_branch(t));
		}
	}
	#d() {
		var t = [];
		for (let a of this.#a) if (!(a.f & 16384 || !(a.f & 6144))) {
			for (var n = a, r = !1; n.parent !== null;) {
				n = n.parent;
				var i = n.f;
				if (i & 96) {
					if (!(i & 1024)) {
						r = !0;
						break;
					}
					n.f ^= e;
				}
			}
			r || t.push(n);
		}
		return this.#a = [], t;
	}
	#f() {
		if (I = kt = this, L?.derived_cache.clear(), this.started = !0, Ut = this.id, this.#i.size > 0) {
			for (let [e, t] of this.#i) this.#S(e, t);
			this.#i.clear();
		}
		this.activate();
		for (var e = Lt = [], t = [], i = [], a = Rt = []; this.#a.length > 0;) {
			zt++ > 1e3 && (this.#T(), Kt());
			for (let n of this.#d()) try {
				this.#m(n, e, t, i);
			} catch (e) {
				throw en(n, !0), this.#l() || this.discard(), e;
			}
			if (this.#a.length > 0) {
				for (let e of t) this.#a.push(e);
				for (let t of e) this.#a.push(t);
				t.length = 0, e.length = 0;
			}
		}
		if (I = null, a.length > 0) {
			var o = r.ensure();
			for (let e of a) e.f & 1024 || o.schedule(e, n);
		}
		if (Lt = null, Rt = null, this.merge_requests.size > 0) {
			let n = Array.from(this.merge_requests, M).filter((e) => e !== this && e.linked && !e.is_fork).sort((e, t) => e.id - t.id);
			if (this.merge_requests.clear(), n.length > 0) {
				this.#y(t), this.#y(e);
				for (var s = this, c = n.length; c--;) {
					var l = n[c];
					l !== s && (l.#_(s), s = l);
				}
				s.#f();
				return;
			}
		}
		if (this.#l()) {
			this.#y(t), this.#y(e);
			for (let e of this.#o) en(e);
			a.length > 0 && I.#f();
			return;
		}
		let u = this.#h();
		if (u) this.#y(t), this.#y(e), u.#_(this), u.#f();
		else {
			for (let t of i) t.is_pending && t.is_ready(this) && t.reveal(e);
			this.#C(!0), this.#x(this.#e), Xt(e, Xt(t)), this.#r?.resolve();
			var d = I;
			if (this.#n.size === 0 && (this.#a.length === 0 || d !== null) && this.#T(), d !== null) {
				if (L !== null) for (let [e, t] of L.reverted_values) d.previous.get(e)?.wv !== t.wv && L.reverted_values.delete(e);
				d.#f();
			}
		}
	}
	#p(e) {
		var t = new Set(e), r = /* @__PURE__ */ new Set();
		for (let e of t) {
			var i = e.reactions;
			if (i !== null) for (let e of i) {
				var a = e.f;
				if (a & 2) a & 1024 && N(e, n), t.add(e);
				else {
					var o = e;
					r.has(o) || (r.add(o), !(a & 155648) && !this.is_skipped(o) && this.schedule(o, n));
				}
			}
		}
	}
	#m(t, n, r, i) {
		t.f ^= e;
		for (var a = t.first; a !== null;) {
			var o = a.f, s = !!(o & 96);
			if (!(s && o & 1024 || o & 139264 || this.#u(a)) && a.fn !== null) {
				s ? a.f ^= e : o & 4 ? n.push(a) : Xn(a) && yr(a);
				var c = a.first;
				if (c !== null) {
					a = c;
					continue;
				}
			}
			for (; a !== null;) {
				if ((a.f & 16512) == 128) {
					var l = a.b;
					l.is_pending && l.is_ready(this) && i.push(l);
				}
				var u = a.next;
				if (u !== null) {
					a = u;
					break;
				}
				a = a.parent;
			}
		}
	}
	#h() {
		for (var e = this.prev; e !== null; e = e.prev) if (!e.is_fork && this.#g(e)) return e;
		return null;
	}
	#g(e) {
		for (let t of this.current.keys()) if (e.current.has(t)) return !0;
		return !1;
	}
	#_(e) {
		for (let t of e.merge_requests) this.merge_requests.add(t);
		e.merge_requests.clear();
		for (let [t, n] of e.current) {
			if (!this.previous.has(t)) {
				let n = e.previous.get(t);
				n && this.previous.set(t, n);
			}
			this.current.set(t, n);
		}
		for (let [t, n] of e.async_deriveds) {
			let e = this.async_deriveds.get(t);
			e && e !== n && n.promise.then(e.resolve, e.reject), this.async_deriveds.set(t, n);
		}
		for (let [n, r] of e.records ?? []) if (!(n.f & 16)) {
			var t = this.records?.get(n);
			(this.records ??= /* @__PURE__ */ new Map()).set(n, r), e.records?.delete(n), $n(n, t);
		}
		if (e.async_deriveds.clear(), e.#n.size > 0) {
			for (let [t, n] of e.#n) this.#n.set(t, (this.#n.get(t) ?? 0) + n);
			e.#n.clear();
		}
		if (e.#i.size > 0) {
			for (let [t, n] of e.#i) this.#v(t, n);
			e.#i.clear();
		}
		let n = () => e.discard();
		this.oncommit(n), this.ondiscard(n), e.merged = this, e.#T();
	}
	#v(e, t) {
		(t === 2048 || this.#i.get(e) !== 2048) && this.#i.set(e, t);
	}
	#y(r) {
		for (var i = 0; i < r.length; i += 1) {
			var a = r[i], o = a.f & (t | n);
			o !== 0 && (this.#v(a, a.dv === null ? n : o), N(a, e));
		}
	}
	capture(e, n, r, i = !1, a = null) {
		var o = this.previous.get(e), s = Zt(this, e);
		o === void 0 && (o = s?.previous.get(e), o === void 0 && e.v !== E && (o = {
			v: e.v,
			wv: e.wv,
			e: (e.f & f) !== 0,
			assigned: (e.f & m) !== 0
		}), o !== void 0 && this.previous.set(e, o)), Mn ? Mt(e) : o !== void 0 && (L?.reverted_values.set(e, o), L?.derived_cache.clear());
		var c = {
			v: n,
			wv: r ? e.wv : Gn(),
			e: i,
			assigned: !!(e.f & 2),
			async: (e.f & d) !== 0
		};
		this.current.set(e, c), R?.set(e, c), Nt?.delete(e), !this.is_fork && s !== null && s.previous.set(e, c), !this.is_fork && !r && s === null && Qt(e, c), r || (Bt = null, Vt = 0, this.mark(e, t, a), Bt = null, vt.size > 0 && !yt && Tt());
	}
	deactivate() {
		I = kt = R = Nt = z = null;
	}
	flush() {
		var e = jt(this.previous);
		try {
			if (this.#f(), Ft.size > 0) for (let e of Ft) Ft.delete(e), e.linked && !e.#c && e.#f();
		} finally {
			zt = 0, Pt = null, Lt = null, Rt = null, L = e.parent, this.deactivate();
		}
	}
	discard() {
		this.#x(this.#t);
		for (let e of this.async_deriveds.values()) e.reject(ct);
		this.#T(), this.#r?.resolve();
	}
	#b() {
		for (let i = F; i !== null; i = i.next) if (i !== this) {
			var e = i.id < this.id, t = [];
			for (let [r, a] of this.current) {
				var n = i.current.get(r);
				if (n !== void 0) {
					if (e && a.v !== n.v && !n.async) i.current.set(r, a);
					else continue;
				}
				t.push(r);
			}
			if (i.started && i.current.size !== 0) {
				var r = !0;
				for (let e of i.current.keys()) if (!this.current.has(e)) {
					r = !1;
					break;
				}
				r && e ? i.discard() : t.length > 0 && (i.#p(t), Ft.add(i));
			}
		}
		this.current.clear(), this.previous.clear();
	}
	commit_writes() {
		this.#b(), this.linked && this.prev !== null && this.#w();
	}
	increment(e) {
		var t = this.#n.get(e) ?? 0;
		this.#n.set(e, t + 1);
	}
	decrement(e) {
		var t = this.#n.get(e) ?? 0;
		t === 1 ? this.#n.delete(e) : this.#n.set(e, t - 1), this.#c || (this.#c = !0, Je(() => {
			this.#c = !1, this.linked && this.flush();
		}));
	}
	oncommit(e) {
		this.#e.set(e, Jt?.size ? Jt : null);
	}
	ondiscard(e) {
		this.#t.set(e, Jt?.size ? Jt : null);
	}
	#x(e) {
		X(() => {
			for (let [n, r] of e) if (r === null) n(this);
			else {
				var t = jt();
				for (let [e, n] of r) t.reverted_values.has(e) && t.reverted_values.set(e, n);
				try {
					n(this);
				} finally {
					L = t.parent;
				}
			}
		}), e.clear();
	}
	settled() {
		return (this.#r ??= we()).promise;
	}
	static ensure() {
		if (I === null) {
			let e = I = new r();
			kt === null && !It && Je(() => {
				e.started || e.flush();
			});
		}
		return I;
	}
	activate() {
		I = this, z = this, Ut !== this.id && (Ut = null), R = Nt = null;
	}
	get_record(e) {
		for (var t = this.records?.get(e), n = this.folded.length; t === void 0 && n--;) t = this.folded[n].records?.get(e);
		return t;
	}
	mark(e, r, i = null) {
		var a = e.reactions;
		if (a !== null) {
			var o = Ge(), s = a.length;
			if (Vt += s, Vt > 1e5 && Bt === null && (Bt = /* @__PURE__ */ new Set()), Bt !== null) {
				if (Bt.has(e)) return;
				Bt.add(e);
			}
			for (var c = 0; c < s; c++) {
				var l = a[c], u = l.f;
				if (o || l !== W) {
					var d = (u & t) === 0;
					if (u & 131072) this.is_fork || (d && N(l, r), vt.add(l));
					else if (u & 2) {
						d && N(l, r);
						var f = l;
						Nt?.delete(f), this.mark(f, n, i);
					} else if (d) {
						var p = l;
						u & 16 && qt !== null && (N(p, r), qt.add(p)), i === null ? this.schedule(p, r) : (N(p, r), i.push(p));
					}
				}
			}
		}
	}
	schedule(e, t) {
		if (Pt = e, z !== null && z !== this && e !== H) this.#v(e, e.f & 2097152 ? t : n);
		else {
			if (kt !== this && H === null) {
				if (this.prev !== null || this.next !== null || this.is_fork) {
					this.#v(e, n);
					return;
				}
				t = n;
			}
			this.#S(e, t);
		}
	}
	#S(e, t) {
		e.f & 2048 || N(e, t), this.#a.push(e);
	}
	#C(e = !1) {
		var t = this.records;
		if (t !== null) {
			this.records = null;
			for (let [r, i] of t) {
				if (!(r.f & 16386)) {
					var n = !!(r.f & 4194304) && nr(i) && !nr(r);
					if (e && !n && (pr(r, i), r.f & 4194304)) for (let e = F; e !== null; e = e.next) e !== this && !e.records?.has(r) && e.async_deriveds.get(r)?.reject(ct);
					hr(r);
				}
				$n(r, i);
			}
		}
	}
	#w() {
		var e = this.prev, t = F;
		e.next = this.next, this.next === null ? Ot = e : this.next.prev = e, this.prev = null, this.next = t, t.prev = F = this, this.id = t.id - 1;
	}
	#T() {
		if (this.linked) {
			var e = this.prev, t = this.next;
			e === null ? F = t : e.next = t, t === null ? Ot = e : t.prev = e, this.linked = !1, this.#C();
		}
	}
};
function Gt(e) {
	var t = It, n = z === I ? null : z;
	It = !0;
	try {
		var r;
		for (e && (Gt(), r = e());;) {
			if (Ye(), I === null) return r;
			I.flush();
		}
	} finally {
		It = t, z = n;
	}
}
function Kt() {
	try {
		Me();
	} catch (e) {
		Ee(e, Pt);
	}
}
var qt = null, Jt = null;
function Yt(e) {
	if ((e.f & 32772) != 4) return !1;
	for (var t = e.b; t !== null; t = t.parent) if (t.is_pending) return t.defer_effect(e), !0;
	return !1;
}
function Xt(e, t = null) {
	var n = e.length;
	if (n === 0) return t;
	for (var r = 0; r < n;) {
		var i = e[r++];
		if (!(i.f & 24576) && !I?.is_skipped(i) && !Yt(i) && Xn(i)) {
			qt = /* @__PURE__ */ new Set();
			var a = Vn;
			if (yr(i), i.edges === null && i.first === null && i.nodes === null && i.teardown === null && i.ac === null && xn(i), qt?.size > 0) {
				var o = L;
				t !== null && jt(t);
				var s = Jt;
				Jt = new Map(t);
				try {
					for (let e of qt) {
						if (e.f & 24576 || I?.is_skipped(e)) continue;
						let t = [e], n = e.parent;
						for (; n !== null;) qt.has(n) && (qt.delete(n), t.push(n)), n = n.parent;
						for (let e = t.length - 1; e >= 0; e--) {
							let n = t[e];
							n.f & 24576 || I?.is_skipped(n) || yr(n);
						}
					}
				} finally {
					Jt = s, qt?.clear(), L = o;
				}
			}
			if (Vn !== a && I !== null) for (let [e, n] of I.current) n.wv > a && (t ??= /* @__PURE__ */ new Map()).set(e, n);
		}
	}
	return qt = null, t;
}
function Zt(e, t) {
	for (var n = e.next; n !== null && (n.is_fork || !n.current.has(t));) n = n.next;
	return n;
}
function Qt(e, t) {
	e.v = t.v, e.wv = t.wv, e.f = t.e ? e.f | f : e.f & ~f, e.f & 2 && (e.f |= m, ot(e));
}
function $t(e) {
	var t = R, n = Nt, r = z;
	R = Nt = z = null;
	try {
		e();
	} finally {
		R = t, Nt = n, z = r;
	}
}
function en(t, n = !1) {
	if (!(!n && t.f & 32 && t.f & 1024)) {
		N(t, e);
		for (var r = t.first; r !== null;) en(r, n), r = r.next;
	}
}
// node_modules/svelte/src/internal/client/reactivity/effects.js
function tn(e) {
	W === null && (H === null && je(e), Ae()), Mn && ke(e);
}
function nn(e, t) {
	var n = t.last;
	n === null ? t.last = t.first = e : (n.next = e, e.prev = n, t.last = e);
}
function rn(e, n) {
	var i = W;
	i !== null && i.f & 8192 && (e |= r);
	var a = {
		ctx: j,
		deps: null,
		dv: null,
		edges: null,
		nodes: null,
		f: e | t | 512,
		first: null,
		fn: n,
		last: null,
		next: null,
		parent: i,
		b: i && i.b,
		prev: null,
		teardown: null,
		wv: 0,
		ac: null,
		r: $e
	}, s = a;
	if (e & 4) Lt === null ? Wt.ensure().schedule(a, t) : Lt.push(a);
	else if (n !== null) {
		try {
			yr(a);
		} catch (e) {
			throw V(a), e;
		}
		s.edges === null && s.teardown === null && s.nodes === null && s.first === s.last && !(s.f & 524288) && (s = s.first, e & 16 && e & 65536 && s !== null && (s.f |= o));
	}
	if (s !== null && (s.parent = i, i !== null && nn(s, i), H !== null && H.f & 2 && !(e & 64))) {
		var c = H;
		(c.effects ??= []).push(s);
	}
	return a;
}
function an() {
	return H !== null && !In;
}
function on(t) {
	let n = rn(8, null);
	return N(n, e), n.teardown = t, n;
}
function sn(e) {
	tn("$effect");
	var t = W.f;
	if (!H && t & 32 && j !== null && !j.i) {
		var n = j;
		(n.e ??= []).push(e);
	} else return cn(e);
}
function cn(e) {
	return rn(4 | c, e);
}
function ln(e) {
	return tn("$effect.pre"), rn(8 | c, e);
}
function un(e) {
	Wt.ensure();
	let t = rn(64 | s, e);
	return () => {
		V(t);
	};
}
function dn(e) {
	Wt.ensure();
	let t = rn(64 | s, e);
	return (e = {}) => new Promise((n) => {
		e.outro ? Sn(t, () => {
			V(t), n(void 0);
		}) : (V(t), n(void 0));
	});
}
function fn(e) {
	return rn(4, e);
}
function pn(e) {
	return rn(d | s, e);
}
function mn(e, t = 0) {
	return rn(8 | t, e);
}
function hn(e, t = [], n = [], r = []) {
	et(r, t, n, (t) => {
		rn(8, () => {
			e(...t.map(Y));
		});
	});
}
function gn(e, t = 0) {
	return rn(16 | t, e);
}
function B(e) {
	return rn(32 | s, e);
}
function _n(e) {
	var t = e.teardown;
	if (t !== null) {
		let n = Mn, r = Nn, i = L, a = H;
		Pn(!0), U(null);
		try {
			t.call(null);
		} catch (t) {
			Ee(t, e.parent);
		} finally {
			Pn(n, r), At(i), U(a);
		}
	}
}
function vn(e, t = !1) {
	var n = e.first;
	for (e.first = e.last = null; n !== null;) {
		ir(n);
		var r = n.next;
		n.f & 64 ? n.parent = null : V(n, t), n = r;
	}
}
function yn(e) {
	for (var t = e.first; t !== null;) {
		var n = t.next;
		t.f & 32 || V(t), t = n;
	}
}
function V(e, t = !0) {
	var n = !1;
	try {
		(t || e.f & 262144) && e.nodes !== null && e.nodes.end !== null && (bn(e.nodes.start, e.nodes.end), n = !0), e.f |= a, vn(e, t && !n), vr(e);
		var r = e.nodes && e.nodes.t;
		if (r !== null) for (let e of r) e.stop();
		_n(e);
	} finally {}
	e.f ^= a, e.f |= 16384;
	var i = e.parent;
	i !== null && i.first !== null && xn(e), e.next = e.prev = e.teardown = e.ctx = e.deps = e.dv = e.edges = e.fn = e.nodes = e.ac = e.b = e.r = null;
}
function bn(e, t) {
	for (; e !== null;) {
		var n = e === t ? null : /* @__PURE__ */ Fr(e);
		Qr(e), e = n;
	}
}
function xn(e) {
	var t = e.parent, n = e.prev, r = e.next;
	n !== null && (n.next = r), r !== null && (r.prev = n), t !== null && (t.first === e && (t.first = r), t.last === e && (t.last = n));
}
function Sn(e, t, n = !0) {
	var r = [];
	e.f |= 256, Cn(e, r, !0);
	var i = () => {
		n && V(e), t && t();
	}, a = r.length;
	if (a > 0) {
		var o = L, s = () => {
			if (!--a) {
				var e = L;
				try {
					o && (o.derived_cache.clear(), At(o)), i();
				} finally {
					o && At(e);
				}
			}
		};
		for (var c of r) c.out(s);
	} else i();
}
function Cn(e, t, n) {
	if (!(e.f & 8192)) {
		e.f ^= r;
		var i = e.nodes && e.nodes.t;
		if (i !== null) for (let e of i) (e.is_global || n) && t.push(e);
		for (var a = e.first; a !== null;) {
			var o = a.next;
			if (!(a.f & 64)) {
				var s = !!(a.f & 65536) || !!(a.f & 32) && !!(e.f & 16);
				Cn(a, t, s ? n : !1);
			}
			a = o;
		}
	}
}
function wn(e) {
	e.f &= -257, Tn(e, !0);
}
function Tn(e, t) {
	if (!(e.f & 256) && e.f & 8192) {
		e.f ^= r, e.f & 1024 || Wt.ensure().schedule(e, n);
		for (var i = e.first; i !== null;) {
			var a = i.next, o = !!(i.f & 65536) || !!(i.f & 32);
			Tn(i, o ? t : !1), i = a;
		}
		var s = e.nodes && e.nodes.t;
		if (s !== null) for (let e of s) (e.is_global || t) && e.in();
	}
}
function En(e, t) {
	if (e.nodes) try {
		for (var n = e.nodes.start, r = e.nodes.end; n !== null;) {
			var i = n === r ? null : /* @__PURE__ */ Fr(n);
			Yr(t, n), n = i;
		}
	} finally {}
}
// node_modules/svelte/src/internal/client/legacy.js
var Dn = null, On = !1;
function kn() {
	On || (On = !0, li(document, "reset", (e) => {
		Promise.resolve().then(() => {
			if (!e.defaultPrevented) for (let t of e.target.elements) t[C]?.();
		});
	}, { capture: !0 }));
}
// node_modules/svelte/src/internal/client/dom/elements/bindings/shared.js
function An(e) {
	var t = H, n = W;
	U(null), Ln(null);
	try {
		return e();
	} finally {
		U(t), Ln(n);
	}
}
function jn(e, t, n, r = n) {
	e.addEventListener(t, () => An(n));
	let i = e[C];
	e[C] = i ? () => {
		i(), r(!0);
	} : () => r(!0), kn();
}
// node_modules/svelte/src/internal/client/runtime.js
var Mn = !1, Nn = 0;
function Pn(e, t = Vn) {
	Mn = e, Nn = t;
}
var Fn = {
	v: void 0,
	wv: 0,
	e: !1,
	assigned: !1
}, H = null, In = !1;
function U(e) {
	H = e;
}
var W = null;
function Ln(e) {
	W = e;
}
var Rn = null;
function zn(e) {
	H !== null && (H.f & 2097152 || H.f & 2) && (Rn ??= /* @__PURE__ */ new Set()).add(e);
}
var G = null, K = 0, q = null;
function Bn(e) {
	q = e;
}
var Vn = 1, Hn = 0, Un = Hn;
function Wn(e) {
	Un = e;
}
function Gn() {
	return ++Vn;
}
function Kn(e) {
	return R === null ? (mt(e), e.wv) : e.f & 2 ? ht(e).wv : (R.get(e) ?? e).wv;
}
function qn(e, t) {
	if (e !== null) {
		for (var n = 0; n < t.length; n++) if (Kn(e[n]) !== t[n]) return !1;
	}
	return !0;
}
function Jn(e, t, n = null) {
	if (e !== null) for (var r = 0; r < e.length; r++) {
		var i = e[r];
		if (i.f & 2) {
			var a = i;
			if (R === null ? mt(i) : a = ht(i), a.wv > t) {
				if (a === i ? i.f & 67108864 : !("dv" in a)) return !0;
				if (n === null) n = /* @__PURE__ */ new Set();
				else if (n.has(a)) continue;
				if (Jn(a.deps, t, n)) return !0;
				n.add(a);
			}
		} else if (Kn(i) > t) return !0;
	}
	return !1;
}
function Yn(e) {
	return !!(e.f & 4194320) && z?.get_record(e) || e;
}
function Xn(t) {
	var n = t.f;
	if (!(n & 6144)) return !1;
	if (n & 67108864) {
		if (Jn(t.deps, t.wv)) return !0;
	} else if (n & 2048) return !0;
	else {
		var r = Yn(t), i = r.deps, a = r.dv;
		if (a === null) return !0;
		if (R === null) for (var o = 0, s = a.length; o < s; o++) {
			var c = i[o];
			if (mt(c), c.wv !== a[o]) return !0;
		}
		else if (!qn(i, a)) return !0;
	}
	return n & 512 && N(t, e), !1;
}
function Zn(e, r, i = !0) {
	var a = e.reactions;
	if (a !== null && !(Rn !== null && Rn.has(e))) for (var o = 0; o < a.length; o++) {
		var s = a[o];
		s.f & 2 ? Zn(s, r, !1) : r === s && I.schedule(s, i ? t : n);
	}
}
var J = null;
function Qn(e) {
	e && An(() => e.abort(w));
}
function $n(e, t, n = !1) {
	if (t?.ac) {
		for (var r = F; r !== null; r = r.next) if (r.records?.get(e) === t && (!n || r !== z && !rr(I, r))) return;
		Qn(t.ac), t.ac = null;
	}
}
function er(e, t) {
	var n = I, r = !!(t & 2);
	if (!(r && Mn)) {
		var i = n === null || !n.is_fork;
		$n(e, z?.records?.get(e), !0), (r ? R === null || i && nr(e) : i) && Qn(e.ac);
		for (var a = F; a !== null; a = a.next) rr(n, a) && $n(e, a.records?.get(e), !0);
	}
}
function tr(e) {
	Qn(e.ac), e.ac = J;
}
function nr({ deps: e, dv: t }) {
	return t === null || t.some((t, n) => e[n].wv !== t);
}
function rr(e, t) {
	return e !== null && !e.is_fork && !t.is_fork && t.id < e.id && (R === null || t.previous.size === 0 || e.folded.includes(t));
}
function ir(e) {
	if (!(e.f & 134217728)) return !1;
	e.f ^= p, Qn(e.ac), e.ac = null;
	for (var t = F; t !== null; t = t.next) {
		var n = t.records?.get(e);
		n?.ac && (Qn(n.ac), n.ac = null);
	}
	return !0;
}
function ar(e) {
	return !(e & 4194304) && (e & 32784) != 32784 ? !1 : z !== null && z === I;
}
function or(e) {
	let t = I;
	var n = G, r = K, a = q, o = H, s = Rn, c = j, l = In, d = Un, f = e.f;
	G = null, K = 0, q = null, H = f & 96 ? null : e, Rn = null, Ve(e.ctx), In = !1, Un = ++Hn;
	var p = J;
	J = null, f & 134217728 && er(e, f);
	try {
		e.f |= u;
		var m = e.fn, h = m();
		if (e.f |= i, sr(e, f, h, !1), Ge() && q !== null && !In && (G !== null || K > 0) && !(e.f & 6146)) for (var g = 0; g < q.length; g++) Zn(q[g], e);
		if (o !== null && o !== e) {
			if (Hn++, o.deps !== null) for (let e = 0; e < r; e += 1) o.deps[e].rv = Hn;
			if (n !== null) for (let e of n) e.rv = Hn;
			q !== null && (a === null ? a = q : a.push(...q));
		}
		return h;
	} catch (t) {
		var _ = t;
		try {
			_ = Te(t);
		} finally {
			sr(e, f, _, _ === t);
		}
		return _;
	} finally {
		var v = J?.signal;
		t !== null && v !== void 0 && v.addEventListener("abort", () => {
			if (I !== null) {
				let e = M(t);
				e !== I && e.linked && !e.is_fork && I.merge_requests.add(e);
			}
		}), e.f ^= u, G = n, K = r, q = a, H = o, Rn = s, Ve(c), In = l, Un = d, J = p;
	}
}
function sr(e, t, n, r) {
	var i = e.deps, a = K + (G === null ? 0 : G.length), o = e.dv;
	if (e.f & 16384) Qn(J);
	else if (J !== null && !(e.f & 134217728) && (Qn(J), J = null), t & 2 && Mn) {
		for (var s = 0, c = 0; c < a; c++) {
			var l = c < K ? i[c] : G[c - K];
			s = Math.max(s, wr(l));
		}
		Fn = {
			v: n,
			wv: s,
			e: r,
			assigned: (t & m) !== 0
		};
	} else if (t & 2 && R === null && F !== null && F.next !== null && ur(e, t), G === null && R === null && o !== null && a === i?.length && e.edges === i && !(t & 4194320)) {
		for (var u = 0; u < a; u++) o[u] = i[u].wv;
		o.length !== a && (o.length = a), t & 2 && cr(e, n, r), (e.ac || J) && tr(e);
	} else lr(e, t, a, n, r);
}
function cr(e, t, n) {
	var r = e.f & ~m;
	(n || r & 8388608 || !e.equals(t)) && (e.v = t, e.wv = Gn(), r = n ? r | f : r & ~f), e.f = r, ot(e);
}
function lr(e, t, n, r, i) {
	var a = ar(t);
	if (R !== null && t & 2) {
		var o = R.get(e);
		o !== void 0 && o.wv !== e.wv && (a = !0);
	}
	var s = e.deps, c = s;
	(G !== null || K !== s?.length) && (c = K === 0 ? G : s.slice(0, K).concat(G ?? []));
	for (var l = !a && R === null && e.dv !== null ? e.dv : [], u = 0; u < n; u++) {
		var d = c[u];
		l[u] = dr(d), R !== null && t & 2 && (l[u] !== d.wv || (d.f & 1026) == 2) && (a = !0);
	}
	l.length !== n && (l.length = n), !a && R !== null && t & 2 && ur(e, t);
	var f = a || mr(e), p = an() && !!(e.f & 512), m = e.edges;
	if (f && m !== null) {
		if (G !== null) {
			e.edges = m = m.slice();
			for (d of G) de.call(m, d) || (m.push(d), p && (d.reactions ??= []).push(e));
		}
	} else {
		if (m === s) {
			if (m !== null) for (u = K; u < m.length; u++) _r(e, m[u]);
			if (p && G !== null) for (d of G) (d.reactions ??= []).push(e);
		} else {
			var h = new Set(c);
			for (d of m) h.delete(d) || _r(e, d);
			if (p) for (d of h) (d.reactions ??= []).push(e);
		}
		e.edges = c;
	}
	if (a) {
		var g = z;
		(g.records ??= /* @__PURE__ */ new Map()).set(e, t & 2 ? {
			deps: c,
			dv: l,
			v: r,
			e: i,
			wv: fr(e, g, r, i),
			ac: J
		} : {
			deps: c,
			dv: l,
			ac: J
		});
	} else e.deps = c, e.dv = l, (e.ac || J) && tr(e), t & 2 && (cr(e, r, i), z?.records?.delete(e));
}
function ur(e, t) {
	var n = e.dv;
	if (!(n === null || n.length === 0 || t & 67108864)) {
		for (var r, i = e.ac, a = i !== null && I !== null && I.is_fork && !i.signal.aborted, o = F; o !== null; o = o.next) o !== z && !o.records?.has(e) && (i === null || a || rr(I, o)) && (r ??= {
			deps: e.deps,
			dv: n.slice(),
			v: e.v,
			wv: e.wv,
			e: (t & f) !== 0
		}, (o.records ??= /* @__PURE__ */ new Map()).set(e, r));
		a && r !== void 0 && (r.ac = i, e.ac = null);
	}
}
function dr(e) {
	return R === null ? e.wv : e.f & 2 ? Nt.get(e)?.wv ?? -1 : (R.get(e) ?? e).wv;
}
function fr(e, t, n, r) {
	if (!r) {
		var i = t.get_record(e);
		if (i !== void 0 && !i.e && e.equals.call(i, n)) return i.wv;
		if (!(e.f & 8388608) && e.equals(n)) return e.wv;
	}
	return Gn();
}
function pr(e, t) {
	if (e.deps = t.deps, e.dv = e.f & 2 ? t.dv.slice() : t.dv, e.f & 2) {
		var n = e;
		n.v = t.v, n.wv = t.wv, n.f = (t.e ? n.f | f : n.f & ~f) & ~m, ot(n);
	}
	Qn(e.ac), e.ac = t.ac ?? null, t.ac = null;
}
function mr(e) {
	for (var t = F; t !== null; t = t.next) if (t.records?.has(e)) return !0;
	return !1;
}
function hr(e) {
	var t = e.edges, n = e.deps;
	if (!(t === n || mr(e))) {
		for (var r of t) n !== null && de.call(n, r) || _r(e, r);
		e.edges = n;
	}
}
function gr(e, t) {
	var n = e.reactions ??= [];
	de.call(n, t) || n.push(t);
}
function _r(e, n) {
	let r = n.reactions;
	if (r !== null) {
		var i = ue.call(r, e);
		if (i !== -1) {
			var a = r.length - 1;
			a === 0 ? r = n.reactions = null : (r[i] = r[a], r.pop());
		}
	}
	if (r === null && n.f & 2 && (G === null || !de.call(G, n))) {
		var o = n;
		if (o.f & 512 && (o.f ^= 512), o.v !== E && ot(o), ir(o)) {
			N(o, t), o.dv = null;
			for (var s = F; s !== null; s = s.next) s.records?.delete(o);
			Nt?.delete(o);
		}
		gt(o), vr(o);
	}
}
function vr(e) {
	var t = e.edges;
	if (t !== null) for (var n = 0; n < t.length; n++) _r(e, t[n]);
}
function yr(t) {
	var n = t.f;
	if (!(n & 16384)) {
		N(t, e);
		var r = W;
		W = t;
		try {
			n & 16777232 ? yn(t) : vn(t), _n(t);
			var i = or(t);
			t.teardown = typeof i == "function" ? i : null, t.wv = Vn;
		} finally {
			W = r;
		}
	}
}
async function br() {
	await Promise.resolve(), Gt();
}
function Y(e) {
	var t = !!(e.f & 2);
	Dn?.add(e);
	var n = null;
	if (H !== null && !In && !(W !== null && W.f & 16384) && (Rn === null || !Rn.has(e))) {
		var r = H.deps;
		if (H.f & 2097152) e.rv < Hn && (e.rv = Hn, G === null && r !== null && r[K] === e ? K++ : G === null ? G = [e] : G.push(e));
		else {
			n = H;
			var a = H.edges;
			a !== null && de.call(a, e) || (H.edges = a === null ? [e] : [...a, e]), gr(e, H);
		}
	}
	if (Mn) {
		var o = Cr(e);
		if (o !== void 0) {
			if (o.e) throw o.v;
			return o.v;
		}
	}
	var s;
	if (t) {
		var c = e, l = !(c.f & 512) && !In && H !== null && !!(H.f & 512), u = !(c.f & i);
		l && (c.f |= 512), R === null ? mt(c) : s = ht(c), l && !u && (_t(c), Sr(c));
	} else R !== null && (s = R.get(e));
	if (n !== null && xr(n, e, s === void 0 ? e.wv : s.wv), s !== void 0 && s !== e) {
		if (s.e) throw s.v;
		return s.v;
	}
	if (e.f & 8388608) throw e.v;
	return e.v;
}
function xr(e, t, n) {
	var r = Yn(e), i = r.deps;
	r.dv === null || i !== null && de.call(i, t) || (r.deps = i === null ? [t] : [...i, t], r.dv.push(n));
}
function Sr(e) {
	if (e.f |= 512, e.edges !== null) for (let t of e.edges) gr(t, e), t.f & 2 && !(t.f & 512) && (_t(t), Sr(t));
}
function Cr(e) {
	var t = e.wv > Nn ? void 0 : L?.reverted_values.get(e);
	if (!(e.f & 2)) return t;
	var n = e, r = (L ?? jt()).derived_cache, i = r.get(n);
	if (i !== void 0) return i;
	var a = t ?? R?.get(n), o = a === void 0 ? (n.f & m) !== 0 : a.assigned, s = a === void 0 && !o ? n.dv : null, c = n.deps ?? [], l = o || s !== null, u = s?.length ?? c.length;
	a ??= {
		v: n.v,
		wv: n.wv,
		e: (n.f & f) !== 0,
		assigned: (n.f & m) !== 0
	};
	for (var d = 0; l && d < u; d++) {
		var p = wr(c[d]);
		l = s === null ? p <= a.wv : p === s[d];
	}
	return l ? i = a : (pt(n), i = Fn, a.wv < i.wv && !a.e && !i.e && n.equals.call(a, i.v) && (i.wv = a.wv)), r.set(n, i), i;
}
function wr(e) {
	return (Cr(e) ?? R?.get(e) ?? e).wv;
}
function X(e) {
	var t = In;
	try {
		return In = !0, e();
	} finally {
		In = t;
	}
}
function Tr(e) {
	if (!(typeof e != "object" || !e || e instanceof EventTarget)) {
		if (h in e) Er(e);
		else if (!Array.isArray(e)) for (let t in e) {
			let n = e[t];
			typeof n == "object" && n && h in n && Er(n);
		}
	}
}
function Er(e, t = /* @__PURE__ */ new Set()) {
	if (typeof e == "object" && e && !(e instanceof EventTarget) && !t.has(e)) {
		t.add(e), e instanceof Date && e.getTime();
		for (let n in e) try {
			Er(e[n], t);
		} catch {}
		let n = ye(e);
		if (n !== Object.prototype && n !== Array.prototype && n !== Map.prototype && n !== Set.prototype && n !== Date.prototype) {
			let t = ge(n);
			for (let n in t) {
				let r = t[n].get;
				if (r) try {
					r.call(e);
				} catch {}
			}
		}
	}
}
function Dr(e) {
	if (typeof e != "object" || !e || h in e || g in e) return e;
	let t = ye(e);
	if (t !== _e && t !== ve) return e;
	var n = /* @__PURE__ */ new Map(), r = le(e), i = /* @__PURE__ */ xt(0), a = null, o = Un, s = (e) => {
		if (Un === o) return e();
		var t = H, n = Un;
		U(null), Wn(o);
		var r = e();
		return U(t), Wn(n), r;
	};
	return r && n.set("length", /* @__PURE__ */ xt(e.length, a)), new Proxy(e, {
		defineProperty(e, t, r) {
			"value" in r && r.configurable !== !1 && r.enumerable !== !1 && r.writable !== !1 || Fe();
			var i = n.get(t);
			return i === void 0 ? s(() => {
				var e = /* @__PURE__ */ xt(r.value, a);
				return n.set(t, e), e;
			}) : P(i, r.value, !0), !0;
		},
		deleteProperty(e, t) {
			var r = n.get(t);
			if (r === void 0) {
				if (t in e) {
					let e = s(() => /* @__PURE__ */ xt(E, a));
					n.set(t, e), Dt(i);
				}
			} else P(r, E), Dt(i);
			return !0;
		},
		get(t, r, i) {
			if (r === h) return e;
			var o = n.get(r), c = r in t;
			if (o === void 0 && (!c || he(t, r)?.writable) && (o = s(() => /* @__PURE__ */ xt(Dr(c ? t[r] : E), a)), n.set(r, o)), o !== void 0) {
				var l = Y(o);
				return l === E ? void 0 : l;
			}
			return Reflect.get(t, r, i);
		},
		getOwnPropertyDescriptor(e, t) {
			this.has?.(e, t);
			var r = Reflect.getOwnPropertyDescriptor(e, t), i = n.get(t);
			if (i !== void 0) {
				var a = Y(i);
				if (a === E) return;
				if (r && "value" in r) r.value = a;
				else return {
					enumerable: !0,
					configurable: !0,
					value: a,
					writable: !0
				};
			}
			return r;
		},
		has(e, t) {
			if (t === h) return !0;
			var r = n.get(t), i = r !== void 0 && r.v !== E || Reflect.has(e, t);
			return (r !== void 0 || (W !== null || H !== null) && (!i || he(e, t)?.writable)) && (r === void 0 && (r = s(() => /* @__PURE__ */ xt(i ? Dr(e[t]) : E, a)), n.set(t, r)), Y(r) === E) ? !1 : i;
		},
		set(e, t, o, c) {
			var l = n.get(t), u = t in e;
			if (r && t === "length") for (var d = o; d < l.v; d += 1) {
				var f = n.get(d + "");
				f === void 0 ? d in e && (f = s(() => /* @__PURE__ */ xt(E, a)), n.set(d + "", f)) : P(f, E);
			}
			if (l === void 0) (!u || he(e, t)?.writable) && (l = s(() => /* @__PURE__ */ xt(void 0, a)), P(l, Dr(o)), n.set(t, l));
			else {
				u = l.v !== E;
				var p = s(() => Dr(o));
				P(l, p);
			}
			var m = Reflect.getOwnPropertyDescriptor(e, t);
			if (m?.set && m.set.call(c, o), !u) {
				if (r && typeof t == "string") {
					var h = n.get("length"), g = Number(t);
					Number.isInteger(g) && g >= h.v && P(h, g + 1);
				}
				Dt(i);
			}
			return !0;
		},
		ownKeys(e) {
			Y(i);
			var t = Reflect.ownKeys(e).filter((e) => {
				var t = n.get(e);
				return t === void 0 || t.v !== E;
			});
			for (var [r, a] of n) a.v !== E && !(r in e) && t.push(r);
			return t;
		},
		setPrototypeOf() {
			Ie();
		}
	});
}
var Or, kr, Ar, jr;
function Mr() {
	if (Or === void 0) {
		Or = window, kr = /Firefox/.test(navigator.userAgent);
		var e = Element.prototype, t = Node.prototype, n = Text.prototype;
		Ar = he(t, "firstChild").get, jr = he(t, "nextSibling").get, be(e) && (e[b] = void 0, e[y] = null, e[x] = void 0, e.__e = void 0), be(n) && (n[S] = void 0);
	}
}
function Nr(e = "") {
	return document.createTextNode(e);
}
/*@__NO_SIDE_EFFECTS__*/
function Pr(e) {
	return Ar.call(e);
}
/*@__NO_SIDE_EFFECTS__*/
function Fr(e) {
	return jr.call(e);
}
function Z(e, t) {
	if (!D) return /* @__PURE__ */ Pr(e);
	var n = /* @__PURE__ */ Pr(O);
	if (n === null) n = Yr(O, Nr());
	else if (t && Gr(n) !== 3) {
		var r = Nr();
		return Xr(n, r), k(r), r;
	}
	return t && Ur(n), k(n), n;
}
function Ir(e, t = !1) {
	if (!D) {
		var n = /* @__PURE__ */ Pr(e);
		return Wr(n) && ni(n) === "" ? /* @__PURE__ */ Fr(n) : n;
	}
	if (t) {
		if (Gr(O) !== 3) {
			var r = Nr();
			return O && Xr(O, r), k(r), r;
		}
		Ur(O);
	}
	return O;
}
function Lr(e, t = !1) {
	if (!D) return /* @__PURE__ */ Pr(e);
	var n = Z(e, t);
	return A(e), n;
}
function Q(e, t = 1, n = !1) {
	let r = D ? O : e;
	for (var i; t--;) i = r, r = /* @__PURE__ */ Fr(r);
	if (!D) return r;
	if (n) {
		if (Gr(r) !== 3) {
			var a = Nr();
			return r === null ? i && Zr(i, a) : Xr(r, a), k(a), a;
		}
		Ur(r);
	}
	return k(r), r;
}
function Rr(e) {
	e.textContent = "";
}
function zr() {
	return Jt !== null && !!(W.f & i);
}
function Br(e, t, n) {
	return t == null || t === "http://www.w3.org/1999/xhtml" ? n ? document.createElement(e, { is: n }) : document.createElement(e) : n ? document.createElementNS(t, e, { is: n }) : document.createElementNS(t, e);
}
function Vr() {
	return document.createDocumentFragment();
}
function Hr(e, t, n = "") {
	if (t.startsWith("xlink:")) e.setAttributeNS("http://www.w3.org/1999/xlink", t, n);
	else return e.setAttribute(t, n);
}
function Ur(e) {
	if (e.nodeValue.length < 65536) return;
	let t = e.nextSibling;
	for (; t !== null && Gr(t) === 3;) t.remove(), e.nodeValue += t.nodeValue, t = e.nextSibling;
}
function Wr(e) {
	return e instanceof Comment;
}
function Gr(e) {
	if (e != null) return e.nodeType;
}
function Kr(e) {
	return e.nodeName;
}
function qr(e) {
	return e.lastChild;
}
function Jr(e) {
	return e.parentNode;
}
function Yr(e, t) {
	return e.appendChild(t);
}
function Xr(e, t) {
	e.before(t);
}
function Zr(e, t) {
	e.after(t);
}
function Qr(e) {
	e.remove();
}
function $r(e, t) {
	return e.removeChild(t);
}
function ei(e, t) {
	e.textContent = t;
}
function ti(e, t) {
	e.nodeValue = t;
}
function ni(e) {
	return e.nodeValue;
}
function ri(e, t) {
	return e.getAttribute(t);
}
function ii(e, t) {
	e.removeAttribute(t);
}
function ai(e, t) {
	return e.hasAttribute(t);
}
function oi(e, t) {
	e.innerHTML = t;
}
function si(e, t) {
	return e.cloneNode(t);
}
function ci(e, t) {
	return document.importNode(e, t);
}
function li(e, t, n, r) {
	e.addEventListener(t, n, r);
}
function ui(e, t, n, r) {
	e.removeEventListener(t, n, r);
}
function di(e, t, n) {
	e.classList.toggle(t, n);
}
// node_modules/svelte/src/internal/flags/legacy.js
Mr(), typeof window < "u" && ((globalThis.__svelte ??= {}).v ??= /* @__PURE__ */ new Set()).add("5"), Be(), [.../* @__PURE__ */ "allowfullscreen.async.autofocus.autoplay.checked.controls.default.disabled.formnovalidate.indeterminate.inert.ismap.loop.multiple.muted.nomodule.novalidate.open.playsinline.readonly.required.reversed.seamless.selected.webkitdirectory.defer.disablepictureinpicture.disableremoteplayback".split(".")];
var fi = ["touchstart", "touchmove"];
function pi(e) {
	return fi.includes(e);
}
// node_modules/svelte/src/internal/client/dom/elements/events.js
var mi = Symbol("events"), hi = Symbol("propagation stopped at"), gi = /* @__PURE__ */ new Set(), _i = /* @__PURE__ */ new Set();
function vi(e, t, n, r = {}) {
	var i = $e != null;
	function a(...e) {
		if (i) return An(() => n?.apply(this, e));
		var a = e[0];
		if (r.capture || Ci.call(t, a), r.capture || a[hi] !== t) return An(() => n?.call(this, a));
	}
	return !i && (e.startsWith("pointer") || e.startsWith("touch") || e === "wheel") ? (a.__removed = !1, Je(() => {
		a.__removed || li(t, e, a, r);
	})) : li(t, e, a, r), a;
}
function $(e, t, n, r, i) {
	var a = {
		capture: r,
		passive: i
	}, o = vi(e, t, n, a);
	$e == null && (t === document.body || t === window || t === document || t instanceof HTMLMediaElement) && on(() => {
		o.__removed = !0, ui(t, e, o, a);
	});
}
var yi = /* @__PURE__ */ new Map();
function bi(e) {
	var t = /* @__PURE__ */ new Set(), n = (n) => {
		for (var r = 0; r < n.length; r++) {
			var i = n[r];
			if (!t.has(i)) {
				t.add(i);
				var a = pi(i);
				for (let t of [e, document]) {
					var o = yi.get(t);
					o === void 0 && (o = /* @__PURE__ */ new Map(), yi.set(t, o));
					var s = o.get(i);
					s === void 0 ? (t.addEventListener(i, Ci, { passive: a }), o.set(i, 1)) : o.set(i, s + 1);
				}
			}
		}
	};
	return n(fe(gi)), _i.add(n), () => {
		for (var r of t) for (let t of [e, document]) {
			var i = yi.get(t), a = i.get(r);
			--a == 0 ? (t.removeEventListener(r, Ci), i.delete(r), i.size === 0 && yi.delete(t)) : i.set(r, a);
		}
		_i.delete(n);
	};
}
var xi = null, Si = !1;
function Ci(e) {
	var t = this, n = e.cancelBubble;
	if (!(n && e[hi] === t)) {
		n || delete e[hi];
		var r = t.ownerDocument, i = e.type, a = e.composedPath?.() || [], o = a[0] || e.target;
		xi = e, Si || (Si = !0, setTimeout(() => {
			Si = !1, xi = null;
		}));
		var s = 0, c = xi === e && e[mi];
		if (c) {
			var l = a.indexOf(c);
			if (l !== -1 && (t === document || t === window)) {
				e[mi] = t;
				return;
			}
			var u = a.indexOf(t);
			if (u === -1) return;
			l <= u && (s = l);
		}
		if (o = a[s] || e.target, o !== t) {
			me(e, "currentTarget", {
				configurable: !0,
				get() {
					return o || r;
				}
			});
			var d = H, f = W;
			U(null), Ln(null);
			try {
				for (var p, m = []; o !== null && o !== t;) {
					try {
						var h = o[mi]?.[i];
						h == null || o.disabled && e.target !== o || h.call(o, e);
					} catch (e) {
						p ? m.push(e) : p = e;
					}
					if (e.cancelBubble) {
						n || (e[hi] = t);
						break;
					}
					s++, o = s < a.length ? a[s] : null;
				}
				if (p) {
					for (let e of m) queueMicrotask(() => {
						throw e;
					});
					throw p;
				}
			} finally {
				e[mi] = t, delete e.currentTarget, U(d), Ln(f);
			}
		}
	}
}
// node_modules/svelte/src/internal/client/dom/reconciler.js
var wi = globalThis?.window?.trustedTypes && /* @__PURE__ */ globalThis.window.trustedTypes.createPolicy("svelte-trusted-html", { createHTML: (e) => e });
function Ti(e) {
	return wi?.createHTML(e) ?? e;
}
function Ei(e) {
	var t = Br("template");
	return oi(t, Ti(e.replaceAll("<!>", "<!---->"))), t.content;
}
// node_modules/svelte/src/internal/client/dom/template.js
function Di(e, t) {
	var n = W;
	n.nodes === null && (n.nodes = {
		start: e,
		end: t,
		a: null,
		t: null
	});
}
/*#__NO_SIDE_EFFECTS__*/
function Oi(e, t) {
	var n = !!(t & 1), r = !!(t & 2), i, a = !e.startsWith("<!>");
	return () => {
		if (D) return Di(O, null), O;
		i === void 0 && (i = Ei(a ? e : "<!>" + e), n || (i = /* @__PURE__ */ Pr(i)));
		var t = r || kr ? ci(i, !0) : si(i, !0);
		return n ? Di(/* @__PURE__ */ Pr(t), qr(t)) : Di(t, t), t;
	};
}
function ki(e, t) {
	if (D) {
		var n = W;
		n.f & 32768 && n.nodes.end !== null || (n.nodes.end = O), ae();
	} else e !== null && Xr(e, t);
}
// node_modules/svelte/src/reactivity/create-subscriber.js
function Ai(e) {
	let t = 0, n = bt(0), r;
	return () => {
		an() && (Y(n), mn(() => (t === 0 && (r = X(() => e(() => Dt(n)))), t += 1, () => {
			Je(() => {
				--t, t === 0 && (r?.(), r = void 0, Dt(n));
			});
		})));
	};
}
// node_modules/svelte/src/internal/client/dom/blocks/boundary.js
var ji = o | s;
function Mi(e, t, n, r) {
	new Ni(e, t, n, r);
}
var Ni = class {
	parent;
	is_pending = !1;
	transform_error;
	#e;
	#t = D ? O : null;
	#n;
	#r;
	#i;
	#a = null;
	#o = null;
	#s = null;
	#c = null;
	#l = 0;
	#u = !1;
	#d = [];
	#f = /* @__PURE__ */ new Map();
	#p = null;
	#m = Ai(() => (this.#p = bt(this.#l), () => {
		this.#p = null;
	}));
	constructor(e, t, n, r) {
		this.#e = e, this.#n = t, this.#r = (e) => {
			var t = W;
			t.b = this, t.f |= 128, n(e);
		}, this.parent = W.b, this.transform_error = r ?? this.parent?.transform_error ?? ((e) => e), this.#i = gn(() => {
			if (D) {
				let e = ce(this.#t);
				ae();
				let t = e === "[!";
				if (e.startsWith("[?")) {
					let t = JSON.parse(e.slice(2));
					this.#g(t);
				} else t ? this.#y() : this.#h();
			} else this.#b();
		}, ji), D && (this.#e = O);
	}
	#h() {
		try {
			this.#a = B(() => this.#r(this.#e));
		} catch (e) {
			this.error(e);
		}
	}
	#g(e) {
		let t = this.#n.failed, { reset: n, invoke_onerror: r } = this.#_(e);
		Je(r), t && (this.#s = B(() => {
			t(this.#e, () => e, () => n);
		}));
	}
	#_(e) {
		var t = !1, n = !1;
		let r = () => {
			this.#v() || (t ? re() : (t = !0, n && Re(), this.#s !== null && Sn(this.#s, () => {
				this.#s = null;
			}), this.#x(() => {
				this.#b();
			})));
		};
		return {
			reset: r,
			invoke_onerror: () => {
				if (!this.#v()) try {
					n = !0, this.#n.onerror?.(e, r), n = !1;
				} catch (e) {
					Ee(e, this.#i && this.#i.parent);
				}
			}
		};
	}
	#v() {
		return !!(this.#i.f & 33570816);
	}
	#y() {
		let e = this.#n.pending;
		e && (this.is_pending = !0, this.#o = B(() => e(this.#e)), Je(() => {
			if (!this.#v()) try {
				var e = this.#c = Vr(), t = Nr();
				Yr(e, t), this.#a = this.#x(() => {
					try {
						return B(() => this.#r(t));
					} catch (e) {
						try {
							this.error(e);
						} catch (e) {
							Ee(e, this.#i.parent);
						}
						return null;
					}
				}), this.#a !== null && this.#f.size === 0 && (this.is_pending = !1, Xr(this.#e, e), this.#c = null, Sn(this.#o, () => {
					this.#o = null;
				}));
			} finally {}
		}));
	}
	#b() {
		try {
			if (this.is_pending = this.has_pending_snippet(), this.#l = 0, this.#a = B(() => {
				this.#r(this.#e);
			}), this.#f.size === 0) this.is_pending = !1;
			else {
				let t = this.#n.pending;
				if (t) {
					var e = this.#c = Vr();
					En(this.#a, e), this.#o = B(() => t(this.#e));
				}
			}
		} catch (e) {
			this.error(e);
		}
	}
	defer_effect(e) {
		this.#d.push(e);
	}
	has_pending_snippet() {
		return !!this.#n.pending;
	}
	#x(e) {
		var t = W, n = H, r = j;
		Ln(this.#i), U(this.#i), Ve(this.#i.ctx);
		try {
			return Wt.ensure(), e();
		} finally {
			Ln(t), U(n), Ve(r);
		}
	}
	is_ready(e) {
		if (e.is_fork && this.#f.size > 0) return !1;
		for (let [t, n] of this.#f) if (!t.is_fork) {
			for (let t of n.keys()) if (e.is_blocked_by(t, this.#a)) return !1;
		}
		return !0;
	}
	reveal(e) {
		this.is_pending = !1;
		for (let n of this.#d) N(n, t), e.push(n);
		if (this.#d.length = 0, this.#o && Sn(this.#o, () => {
			this.#o = null;
		}), this.#c) try {
			Xr(this.#e, this.#c), this.#c = null;
		} finally {}
	}
	increment(e, t) {
		var n = this.#f.get(t);
		n === void 0 && this.#f.set(t, n = /* @__PURE__ */ new Map());
		var r = n.get(e) ?? 0;
		n.set(e, r + 1);
	}
	decrement(e, t) {
		var r = this.#f.get(t), i = r.get(e);
		i === 1 ? (r.delete(e), r.size === 0 && this.#f.delete(t), Je(() => {
			this.is_pending && !this.#v() && Wt.ensure().schedule(this.#i, n);
		})) : r.set(e, i - 1);
	}
	update_effect_pending(e) {
		this.#l += e, !this.#p || this.#u || (this.#u = !0, Je(() => {
			this.#u = !1, this.#p && wt(this.#p, this.#l);
		}));
	}
	get_effect_pending() {
		return this.#m(), Y(this.#p);
	}
	error(e) {
		if (e === T || !this.#n.onerror && !this.#n.failed) throw e;
		I?.is_fork ? (this.#a && I.skip_effect(this.#a), this.#o && I.skip_effect(this.#o), this.#s && I.skip_effect(this.#s), I.oncommit(() => {
			this.#v() || this.#S(e);
		})) : this.#S(e);
	}
	#S(e) {
		this.#a &&= (V(this.#a), null), this.#o &&= (V(this.#o), null), this.#s &&= (V(this.#s), null), D && (k(this.#t), oe(), k(se()));
		let t = this.#n.failed, n = (e) => {
			if (this.#v()) return;
			let { reset: n, invoke_onerror: r } = this.#_(e);
			r(), t && !this.#v() && (this.#s = this.#x(() => {
				try {
					return B(() => {
						var r = W;
						r.b = this, r.f |= 128, t(this.#e, () => e, () => n);
					});
				} catch (e) {
					return Ee(e, this.#i.parent), null;
				}
			}));
		};
		Je(() => {
			if (!this.#v()) {
				var t;
				try {
					t = this.transform_error(e);
				} catch (e) {
					Ee(e, this.#i && this.#i.parent);
					return;
				}
				typeof t == "object" && t && typeof t.then == "function" ? t.then(n, (e) => Ee(e, this.#i && this.#i.parent)) : n(t);
			}
		});
	}
};
function Pi(e, t) {
	var n = t == null ? "" : typeof t == "object" ? `${t}` : t;
	n !== (e[S] ??= ni(e)) && (e[S] = n, ti(e, `${n}`));
}
function Fi(e, t) {
	return Li(e, t);
}
function Ii(e, t) {
	t.intro = t.intro ?? !1;
	let n = t.target, r = D, i = O;
	try {
		for (var a = /* @__PURE__ */ Pr(n); a && (Gr(a) !== 8 || ni(a) !== "[");) a = /* @__PURE__ */ Fr(a);
		if (!a) throw T;
		ie(!0), k(a);
		let r = Li(e, {
			...t,
			anchor: a
		});
		return ie(!1), r;
	} catch (r) {
		if (r instanceof Error && r.message.split("\n").some((e) => e.startsWith("https://svelte.dev/e/"))) throw r;
		return r !== T && console.warn("Failed to hydrate: ", r), t.recover === !1 && Ne(), Rr(n), ie(!1), Fi(e, t);
	} finally {
		ie(r), k(i);
	}
}
function Li(e, t) {
	return Ri(e, t);
}
function Ri(e, { target: t, anchor: n, props: r = {}, events: i, context: a, intro: o = !0, transformError: s, renderer: c }) {
	var l = void 0, u = dn(() => {
		var o = n ?? Yr(t, Nr());
		Mi(o, { pending: () => {} }, (t) => {
			He({});
			var n = j;
			if (a && (n.c = a), i && (r.$$events = i), D && Di(t, null), l = e(t, r) || We(), D && (W.nodes.end = O, O === null || Gr(O) !== 8 || ni(O) !== "]")) throw ne(), T;
			Ue();
		}, s);
		var u = c ? null : bi(t);
		return () => {
			if (u?.(), o !== n) {
				var e = Jr(o);
				e && $r(e, o);
			}
		};
	});
	return zi.set(l, u), l;
}
var zi = /* @__PURE__ */ new WeakMap();
function Bi(e, t) {
	let n = zi.get(e);
	return n ? (zi.delete(e), n(t)) : Promise.resolve();
}
// node_modules/svelte/src/internal/client/dom/blocks/branches.js
var Vi = class {
	anchor;
	#e = /* @__PURE__ */ new Map();
	#t = /* @__PURE__ */ new Map();
	#n = /* @__PURE__ */ new Map();
	#r = /* @__PURE__ */ new Set();
	#i = !0;
	#a = null;
	constructor(e, t = !0) {
		this.anchor = e, this.#i = t, this.#a = $e;
	}
	#o = (e) => {
		if (this.#e.has(e)) try {
			var t = this.#e.get(e), n = this.#t.get(t);
			if (n) wn(n), this.#r.delete(t);
			else {
				var r = this.#n.get(t);
				r && (wn(r.effect), this.#t.set(t, r.effect), this.#n.delete(t), Qr(qr(r.fragment)), Xr(this.anchor, r.fragment), n = r.effect, n.f &= ~l);
			}
			this.#s(e);
			for (let [e, r] of this.#t) {
				if (e === t || this.#r.has(e)) continue;
				let i = () => {
					if (Array.from(this.#e.values()).includes(e)) {
						var t = Vr();
						En(r, t), Yr(t, Nr()), this.#n.set(e, {
							effect: r,
							fragment: t
						});
					} else V(r);
					this.#r.delete(e), this.#t.delete(e);
				};
				this.#i || !n ? (this.#r.add(e), Sn(r, i, !1)) : i();
			}
		} finally {}
	};
	#s = (e) => {
		for (let t of this.#e.keys()) t !== e && t.linked || this.#e.delete(t);
		let t = Array.from(this.#e.values());
		for (let [e, n] of this.#n) t.includes(e) || (V(n.effect), this.#n.delete(e));
	};
	ensure(e, t) {
		var n = I, r = zr();
		if (t && !this.#t.has(e) && !this.#n.has(e)) {
			if (r) {
				var i = Vr(), a = Nr();
				Yr(i, a);
				var o = B(() => t(a));
				o.f |= l, n.unskip_new_effect(o), this.#n.set(e, {
					effect: o,
					fragment: i
				});
			} else this.#t.set(e, B(() => t(this.anchor)));
		}
		if (this.#e.set(n, e), r) {
			for (let [t, r] of this.#t) t === e ? n.unskip_effect(r) : n.skip_effect(r);
			for (let [t, r] of this.#n) t === e ? n.unskip_effect(r.effect) : n.skip_effect(r.effect);
			n.oncommit(this.#o), n.ondiscard(this.#s);
		} else D && (this.anchor = O), this.#o(n);
	}
};
function Hi(e) {
	j === null && De("onMount"), ze && j.l !== null ? Ui(j).m.push(e) : sn(() => {
		let t = X(e);
		if (typeof t == "function") return t;
	});
}
function Ui(e) {
	var t = e.l;
	return t.u ??= {
		a: [],
		b: [],
		m: []
	};
}
// node_modules/svelte/src/internal/client/dom/blocks/if.js
function Wi(e, t, n = !1) {
	var r;
	D && (r = O, ae());
	var i = new Vi(e), a = n ? o : 0;
	function s(e, t) {
		if (D) {
			var n = ce(r);
			if (e !== parseInt(n.substring(1))) {
				var a = se();
				k(a), i.anchor = a, ie(!1), i.ensure(e, t), ie(!0);
				return;
			}
		}
		i.ensure(e, t);
	}
	gn(() => {
		var e = !1;
		t((t, n = 0) => {
			e = !0, s(n, t);
		}), e || s(-1, null);
	}, a);
}
// node_modules/svelte/src/internal/shared/attributes.js
var Gi = [..." 	\n\r\f\xA0\v﻿"];
function Ki(e, t, n) {
	var r = e == null ? "" : "" + e;
	if (t && (r = r ? r + " " + t : t), n) {
		for (var i of Object.keys(n)) if (n[i]) r = r ? r + " " + i : i;
		else if (r.length) for (var a = i.length, o = 0; (o = r.indexOf(i, o)) >= 0;) {
			var s = o + a;
			(o === 0 || Gi.includes(r[o - 1])) && (s === r.length || Gi.includes(r[s])) ? r = (o === 0 ? "" : r.substring(0, o)) + r.substring(s + 1) : o = s;
		}
	}
	return r === "" ? null : r;
}
// node_modules/svelte/src/internal/client/dom/blocks/each.js
function qi(e, t) {
	return t;
}
function Ji(e, t, n) {
	for (var r = [], i = t.length, a, o = t.length, s = 0; s < i; s++) {
		let n = t[s];
		Sn(n, () => {
			if (a) {
				if (a.pending.delete(n), a.done.add(n), a.pending.size === 0) {
					var t = e.outrogroups;
					Xi(e, fe(a.done)), t.delete(a), t.size === 0 && (e.outrogroups = null);
				}
			} else --o;
		}, !1);
	}
	if (o === 0) {
		var c = r.length === 0 && n !== null && e.pending.size === 0;
		if (c) {
			var l = n, u = Jr(l);
			Rr(u), Yr(u, l), e.items.clear();
		}
		Xi(e, t, !c);
	} else a = {
		pending: new Set(t),
		done: /* @__PURE__ */ new Set()
	}, (e.outrogroups ??= /* @__PURE__ */ new Set()).add(a);
}
function Yi(e) {
	var t = /* @__PURE__ */ new Set();
	for (let n of e.pending.values()) for (let r of n) t.add(e.items.get(r).e);
	return t;
}
function Xi(e, t, n = !0) {
	for (var r = e.pending.size > 0 ? Yi(e) : void 0, i = 0; i < t.length; i++) {
		var a = t[i];
		r?.has(a) ? (a.f |= l, En(a, Vr()), a !== e.effect.last && (oa(e, a.prev, a.next), oa(e, e.effect.last, a), oa(e, a, null))) : V(t[i], n);
	}
}
function Zi(e, t) {
	if (e.outrogroups !== null) {
		for (let n of e.outrogroups) if (n.pending.has(t) || n.done.has(t)) return !0;
	}
	return !1;
}
var Qi = /* @__PURE__ */ new WeakMap(), $i = {};
function ea() {
	var e = Qi.get($e ?? $i);
	if (e) return e;
	var t = Nr();
	return Qi.set($e ?? $i, t), t;
}
function ta(e, t, n, r, i, a = null) {
	var o = e, s = /* @__PURE__ */ new Map();
	if (t & 4) {
		var c = e;
		o = D ? k(/* @__PURE__ */ Pr(c)) : Yr(c, Nr());
	}
	D && ae();
	var u = null, d = /* @__PURE__ */ dt(() => {
		var e = n();
		return le(e) ? e : e == null ? [] : fe(e);
	}), f = /* @__PURE__ */ new Map(), p = !0;
	function m(e) {
		if (!(_.effect.f & 16384)) {
			try {
				_.pending.delete(e);
				var n = Y(d);
				_.fallback = u, ra(_, n, o, t, r), u !== null && (n.length === 0 ? u.f & 33554432 ? (u.f ^= l, aa(u, null, o)) : wn(u) : Sn(u, () => {
					u = null;
				}));
			} finally {}
			g();
		}
	}
	function h(e) {
		_.pending.delete(e), _.effect.f & 16384 || g();
	}
	function g() {
		for (var e, t = _.effect.last; t !== null;) {
			var n = t.prev;
			if (t.f & 32 && t !== u) {
				if (!(t.f & 33554432)) break;
				e ??= Yi(_), !e.has(t) && !Zi(_, t) && V(t);
			}
			t = n;
		}
	}
	var _ = {
		effect: gn(() => {
			var e = Y(d), c = e.length;
			let g = !1;
			D && ce(o) === "[!" != (c === 0) && (o = se(), k(o), ie(!1), g = !0);
			for (var _ = /* @__PURE__ */ new Set(), v = I, y = zr(), b = 0; b < c; b += 1) {
				D && Gr(O) === 8 && ni(O) === "]" && (o = O, g = !0, ie(!1));
				var x = e[b], S = r(x, b), C = p ? null : s.get(S);
				C ? (C.v && wt(C.v, x), C.i && wt(C.i, b), y && v.unskip_effect(C.e)) : (C = ia(s, p ? o : ea(), x, S, b, i, t, n), p || (C.e.f |= l, y && v.unskip_new_effect(C.e)), s.set(S, C)), _.add(S);
			}
			if (c === 0 && a && !u && (p ? u = B(() => a(o)) : (u = B(() => a(ea())), u.f |= l, y && v.unskip_new_effect(u))), y && u !== null && (c === 0 ? v.unskip_effect(u) : v.skip_effect(u)), c > _.size && Oe("", "", ""), D && c > 0 && k(se()), !p) {
				if (f.set(v, _), y) {
					for (let [e, t] of s) _.has(e) || v.skip_effect(t.e);
					v.oncommit(m), v.ondiscard(h);
				} else m(v);
			}
			g && ie(!0), Y(d);
		}),
		flags: t,
		items: s,
		pending: f,
		outrogroups: null,
		fallback: u
	};
	p = !1, D && (o = O);
}
function na(e) {
	for (; e !== null && !(e.f & 32);) e = e.next;
	return e;
}
function ra(e, t, n, r, i) {
	var a = !!(r & 8), o = t.length, s = e.items, c = na(e.effect.first), u, d = null, f, p = [], m = [], h, g, _, v;
	if (a) for (v = 0; v < o; v += 1) h = t[v], g = i(h, v), _ = s.get(g).e, _.f & 33554432 || (_.nodes?.a?.measure(), (f ??= /* @__PURE__ */ new Set()).add(_));
	for (v = 0; v < o; v += 1) {
		if (h = t[v], g = i(h, v), _ = s.get(g).e, e.outrogroups !== null) for (let t of e.outrogroups) t.pending.delete(_), t.done.delete(_);
		if (_.f & 8192 && (wn(_), a && (_.nodes?.a?.unfix(), (f ??= /* @__PURE__ */ new Set()).delete(_))), _.f & 33554432) {
			if (_.f ^= l, _ === c) aa(_, null, n);
			else {
				var y = d ? d.next : c;
				_ === e.effect.last && (e.effect.last = _.prev), _.prev && (_.prev.next = _.next), _.next && (_.next.prev = _.prev), oa(e, d, _), oa(e, _, y), aa(_, y, n), d = _, p = [], m = [], c = na(d.next);
				continue;
			}
		}
		if (_ !== c) {
			if (u !== void 0 && u.has(_)) {
				if (p.length < m.length) {
					var b = m[0], x;
					d = b.prev;
					var S = p[0], C = p[p.length - 1];
					for (x = 0; x < p.length; x += 1) aa(p[x], b, n);
					for (x = 0; x < m.length; x += 1) u.delete(m[x]);
					oa(e, S.prev, C.next), oa(e, d, S), oa(e, C, b), c = b, d = C, --v, p = [], m = [];
				} else u.delete(_), aa(_, c, n), oa(e, _.prev, _.next), oa(e, _, d === null ? e.effect.first : d.next), oa(e, d, _), d = _;
				continue;
			}
			for (p = [], m = []; c !== null && c !== _;) (u ??= /* @__PURE__ */ new Set()).add(c), m.push(c), c = na(c.next);
			if (c === null) continue;
		}
		_.f & 33554432 || p.push(_), d = _, c = na(_.next);
	}
	if (e.outrogroups !== null) {
		for (let t of e.outrogroups) t.pending.size === 0 && (Xi(e, fe(t.done)), e.outrogroups?.delete(t));
		e.outrogroups.size === 0 && (e.outrogroups = null);
	}
	if (c !== null || u !== void 0) {
		var w = [];
		if (u !== void 0) for (_ of u) _.f & 8192 || w.push(_);
		for (; c !== null;) !(c.f & 8192) && c !== e.fallback && w.push(c), c = na(c.next);
		var ee = w.length;
		if (ee > 0) {
			var T = r & 4 && o === 0 ? n : null;
			if (a) {
				for (v = 0; v < ee; v += 1) w[v].nodes?.a?.measure();
				for (v = 0; v < ee; v += 1) w[v].nodes?.a?.fix();
			}
			Ji(e, w, T);
		}
	}
	a && Je(() => {
		if (f !== void 0) for (_ of f) _.nodes?.a?.apply();
	});
}
function ia(e, t, n, r, i, a, o, s) {
	var c = o & 1 ? o & 16 ? bt(n) : /* @__PURE__ */ St(n, !1, !1) : null, l = o & 2 ? bt(i) : null;
	return {
		v: c,
		i: l,
		e: B(() => (a(t, c ?? n, l ?? i, s), () => {
			e.delete(r);
		}))
	};
}
function aa(e, t, n) {
	if (e.nodes) for (var r = e.nodes.start, i = e.nodes.end, a = t && !(t.f & 33554432) ? t.nodes.start : n; r !== null;) {
		var o = /* @__PURE__ */ Fr(r);
		if (Xr(a, r), r === i) return;
		r = o;
	}
}
function oa(e, t, n) {
	t === null ? e.effect.first = n : t.next = n, n === null ? e.effect.last = t : n.prev = t;
}
// node_modules/svelte/src/internal/client/dom/css.js
function sa(e, t) {
	fn(() => {
		e = W?.parent?.nodes?.start ?? e;
		var n = e.getRootNode(), r = n.host ? n : n.head ?? n.ownerDocument.head;
		if (!r.querySelector("#" + t.hash)) {
			let e = Br("style");
			e.id = t.hash, ei(e, t.code), Yr(r, e);
		}
	});
}
// node_modules/svelte/src/internal/client/dom/elements/class.js
function ca(e, t, n, r, i, a) {
	var o = e[b];
	if (D || o !== n || o === void 0) {
		var s = Ki(n, r, a);
		D && s === ri(e, "class") || (s == null ? ii(e, "class") : t ? e.className = s : Hr(e, "class", s)), e[b] = n;
	} else if (a && i !== a) for (var c in a) {
		var l = !!a[c];
		(i == null || l !== !!i[c]) && di(e, c, l);
	}
	return a;
}
// node_modules/svelte/src/internal/client/dom/elements/attributes.js
var la = Symbol("is custom element"), ua = Symbol("is html"), da = ee ? "link" : "LINK";
function fa(e) {
	if (D) {
		var t = !1, n = () => {
			if (!t) {
				if (t = !0, ai(e, "value")) {
					var n = e.value;
					pa(e, "value", null), e.value = n;
				}
				if (ai(e, "checked")) {
					var r = e.checked;
					pa(e, "checked", null), e.checked = r;
				}
			}
		};
		e[C] = n, Je(n), kn();
	}
}
function pa(e, t, n, r) {
	var i = ma(e);
	if (!(D && (i[t] = ri(e, t), t === "src" || t === "srcset" || t === "href" && Kr(e) === da))) {
		var a = i[t];
		a !== (i[t] = n) && (t === "loading" && (e[v] = n), n == null ? ii(e, t) : typeof n != "string" && ga(e).has(t) ? e[t] = n : (!D || typeof n != "number" && typeof n != "boolean" || a !== String(n)) && Hr(e, t, n));
	}
}
function ma(e) {
	return e[y] ??= {
		[la]: Kr(e).includes("-"),
		[ua]: $e == null && e.namespaceURI === "http://www.w3.org/1999/xhtml"
	};
}
var ha = /* @__PURE__ */ new Map();
function ga(e) {
	var t = ri(e, "is") || Kr(e), n = ha.get(t);
	if (n) return n;
	ha.set(t, n = /* @__PURE__ */ new Set());
	for (var r, i = e, a = Element.prototype; a !== i;) {
		for (var o in r = ge(i), r) r[o].set && o !== "innerHTML" && o !== "textContent" && o !== "innerText" && n.add(o);
		i = ye(i);
	}
	return n;
}
// node_modules/svelte/src/internal/client/dom/elements/bindings/input.js
function _a(e, t, n = t) {
	var r = /* @__PURE__ */ new WeakSet();
	jn(e, "input", async (i) => {
		var a = i ? e.defaultValue : e.value;
		if (a = va(e) ? ya(a) : a, n(a), I !== null && r.add(I), await br(), a !== (a = t())) {
			var o = e.selectionStart, s = e.selectionEnd, c = e.value.length;
			if (e.value = a ?? "", s !== null) {
				var l = e.value.length;
				o === s && s === c && l > c ? (e.selectionStart = l, e.selectionEnd = l) : (e.selectionStart = o, e.selectionEnd = Math.min(s, l));
			}
		}
	}), (D && e.defaultValue !== e.value || X(t) == null && e.value) && (n(va(e) ? ya(e.value) : e.value), I !== null && r.add(I)), mn(() => {
		var n = t();
		e === document.activeElement && r.has(z) || va(e) && n === ya(e.value) || (e.type !== "date" || n || e.value) && n !== e.value && (e.value = n ?? "");
	});
}
function va(e) {
	var t = e.type;
	return t === "number" || t === "range";
}
function ya(e) {
	return e === "" ? null : +e;
}
// node_modules/svelte/src/internal/client/dom/legacy/event-modifiers.js
function ba(e) {
	return function(...t) {
		return t[0].stopPropagation(), e?.apply(this, t);
	};
}
// node_modules/svelte/src/internal/client/dom/legacy/lifecycle.js
function xa(e = !1) {
	let t = j, n = t.l.u;
	if (!n) return;
	let r = () => Tr(t.s);
	if (e) {
		let e = 0, n = {}, i = /* @__PURE__ */ st(() => {
			let r = !1, i = t.s;
			for (let e in i) i[e] !== n[e] && (n[e] = i[e], r = !0);
			return r && e++, e;
		});
		r = () => Y(i);
	}
	n.b.length && ln(() => {
		Sa(t, r), Ce(n.b);
	}), sn(() => {
		let e = X(() => n.m.map(Se));
		return () => {
			for (let t of e) typeof t == "function" && t();
		};
	}), n.a.length && sn(() => {
		Sa(t, r), Ce(n.a);
	});
}
function Sa(e, t) {
	if (e.l.s) for (let t of e.l.s) Y(t);
	t();
}
// node_modules/svelte/src/internal/client/dom/legacy/misc.js
function Ca(e, t) {
	var n = e.$$events?.[t.type];
	for (var r of le(n) ? n.slice() : n == null ? [] : [n]) r.call(this, t);
}
// node_modules/svelte/src/internal/client/reactivity/store.js
var wa = !1;
function Ta(e) {
	var t = wa;
	try {
		return wa = !1, [e(), wa];
	} finally {
		wa = t;
	}
}
// node_modules/svelte/src/internal/client/reactivity/props.js
function Ea(e, t, n, r) {
	var i = !ze || !!(n & 2), a = !!(n & 8), o = !!(n & 16), s = r, c = !0, l = void 0, u = () => o && i ? (l ??= /* @__PURE__ */ st(r), Y(l)) : (c && (c = !1, s = o ? X(r) : r), s);
	let d;
	if (a) {
		var f = h in e || _ in e;
		d = he(e, t)?.set ?? (f && t in e ? (n) => e[t] = n : void 0);
	}
	var p, m = !1;
	a ? [p, m] = Ta(() => e[t]) : p = e[t], p === void 0 && r !== void 0 && (p = u(), d && (i && Pe(t), d(p)));
	var g = i ? () => {
		var n = e[t];
		return n === void 0 ? u() : (c = !0, n);
	} : () => {
		var n = e[t];
		return n !== void 0 && (s = void 0), n === void 0 ? s : n;
	};
	if (i && !(n & 4)) return g;
	if (d) {
		var v = e.$$legacy;
		return (function(e, t) {
			return arguments.length > 0 ? ((!i || !t || v || m) && d(t ? g() : e), e) : g();
		});
	}
	var y = !1, b = (n & 1 ? st : dt)(() => (y = !1, g()));
	a && Y(b);
	var x = W;
	return (function(e, t) {
		if (arguments.length > 0) {
			let n = t ? Y(b) : i && a ? Dr(e) : e;
			return P(b, n), y = !0, s !== void 0 && (s = n), e;
		}
		return Mn && y || x.f & 16384 ? b.v : Y(b);
	});
}
// node_modules/svelte/src/legacy/legacy-client.js
function Da(e) {
	return new Oa(e);
}
var Oa = class {
	#e;
	#t;
	constructor(e) {
		var t = /* @__PURE__ */ new Map(), n = (e, n) => {
			var r = /* @__PURE__ */ St(n, !1, !1);
			return t.set(e, r), r;
		};
		let r = new Proxy({
			...e.props || {},
			$$events: {}
		}, {
			get(e, r) {
				return Y(t.get(r) ?? n(r, Reflect.get(e, r)));
			},
			has(e, r) {
				return r === _ || (Y(t.get(r) ?? n(r, Reflect.get(e, r))), Reflect.has(e, r));
			},
			set(e, r, i) {
				return P(t.get(r) ?? n(r, i), i), Reflect.set(e, r, i);
			}
		}), i = {
			target: e.target,
			anchor: e.anchor,
			props: r,
			context: e.context,
			intro: e.intro ?? !1,
			recover: e.recover,
			transformError: e.transformError
		};
		this.#t = e.hydrate ? Ii(e.component, i) : Fi(e.component, i), e?.props?.$$host && e.sync !== !1 || Gt(), this.#e = r.$$events;
		for (let e of Object.keys(this.#t)) e !== "$set" && e !== "$destroy" && e !== "$on" && me(this, e, {
			get() {
				return this.#t[e];
			},
			set(t) {
				this.#t[e] = t;
			},
			enumerable: !0
		});
		this.#t.$set = (e) => {
			Object.assign(r, e);
		}, this.#t.$destroy = () => {
			Bi(this.#t);
		};
	}
	$set(e) {
		this.#t.$set(e);
	}
	$on(e, t) {
		this.#e[e] = this.#e[e] || [];
		let n = (...e) => t.call(this, ...e);
		return this.#e[e].push(n), () => {
			this.#e[e] = this.#e[e].filter((e) => e !== n);
		};
	}
	$destroy() {
		this.#t.$destroy();
	}
}, ka;
typeof HTMLElement == "function" && (ka = class extends HTMLElement {
	$$ctor;
	$$s;
	$$c;
	$$cn = !1;
	$$d = {};
	$$r = !1;
	$$p_d = {};
	$$l = {};
	$$l_u = /* @__PURE__ */ new Map();
	$$me;
	$$shadowRoot = null;
	constructor(e, t, n) {
		super(), this.$$ctor = e, this.$$s = t, n && (this.$$shadowRoot = this.attachShadow(n));
	}
	addEventListener(e, t, n) {
		if (this.$$l[e] = this.$$l[e] || [], this.$$l[e].push(t), this.$$c) {
			let n = this.$$c.$on(e, t);
			this.$$l_u.set(t, n);
		}
		super.addEventListener(e, t, n);
	}
	removeEventListener(e, t, n) {
		if (super.removeEventListener(e, t, n), this.$$c) {
			let e = this.$$l_u.get(t);
			e && (e(), this.$$l_u.delete(t));
		}
	}
	async connectedCallback() {
		if (this.$$cn = !0, !this.$$c) {
			if (await Promise.resolve(), !this.$$cn || this.$$c) return;
			function e(e) {
				return (t) => {
					let n = Br("slot");
					e !== "default" && (n.name = e), ki(t, n);
				};
			}
			let t = {}, n = ja(this);
			for (let r of this.$$s) r in n && (r === "default" && !this.$$d.children ? (this.$$d.children = e(r), t.default = !0) : t[r] = e(r));
			for (let e of this.attributes) {
				let t = this.$$g_p(e.name);
				t in this.$$d || (this.$$d[t] = Aa(t, e.value, this.$$p_d, "toProp"));
			}
			for (let e in this.$$p_d) !(e in this.$$d) && this[e] !== void 0 && (this.$$d[e] = this[e], delete this[e]);
			this.$$c = Da({
				component: this.$$ctor,
				target: this.$$shadowRoot || this,
				props: {
					...this.$$d,
					$$slots: t,
					$$host: this
				}
			}), this.$$me = un(() => {
				mn(() => {
					this.$$r = !0;
					for (let e of pe(this.$$c)) {
						if (!this.$$p_d[e]?.reflect) continue;
						this.$$d[e] = this.$$c[e];
						let t = Aa(e, this.$$d[e], this.$$p_d, "toAttribute");
						t == null ? this.removeAttribute(this.$$p_d[e].attribute || e) : this.setAttribute(this.$$p_d[e].attribute || e, t);
					}
					this.$$r = !1;
				});
			});
			for (let e in this.$$l) for (let t of this.$$l[e]) {
				let n = this.$$c.$on(e, t);
				this.$$l_u.set(t, n);
			}
			this.$$l = {};
		}
	}
	attributeChangedCallback(e, t, n) {
		this.$$r || (e = this.$$g_p(e), this.$$d[e] = Aa(e, n, this.$$p_d, "toProp"), this.$$c?.$set({ [e]: this.$$d[e] }));
	}
	disconnectedCallback() {
		this.$$cn = !1, Promise.resolve().then(() => {
			!this.$$cn && this.$$c && (this.$$c.$destroy(), this.$$me(), this.$$c = void 0);
		});
	}
	$$g_p(e) {
		return pe(this.$$p_d).find((t) => this.$$p_d[t].attribute === e || !this.$$p_d[t].attribute && t.toLowerCase() === e) || e;
	}
});
function Aa(e, t, n, r) {
	let i = n[e]?.type;
	if (t = i === "Boolean" && typeof t != "boolean" ? t != null : t, !r || !n[e]) return t;
	if (r === "toAttribute") switch (i) {
		case "Object":
		case "Array": return t == null ? null : JSON.stringify(t);
		case "Boolean": return t ? "" : null;
		case "Number": return t ?? null;
		default: return t;
	}
	else switch (i) {
		case "Object":
		case "Array": return t && JSON.parse(t);
		case "Boolean": return t;
		case "Number": return t == null ? t : +t;
		default: return t;
	}
}
function ja(e) {
	let t = {};
	return e.childNodes.forEach((e) => {
		t[e.slot || "default"] = !0;
	}), t;
}
function Ma(e, t, n, r, i, a) {
	let o = class extends ka {
		constructor() {
			super(e, n, i), this.$$p_d = t;
		}
		static get observedAttributes() {
			return pe(t).map((e) => (t[e].attribute || e).toLowerCase());
		}
	};
	return pe(t).forEach((e) => {
		me(o.prototype, e, {
			get() {
				return this.$$c && e in this.$$c ? this.$$c[e] : this.$$d[e];
			},
			set(n) {
				n = Aa(e, n, t), this.$$d[e] = n;
				var r = this.$$c;
				r && (he(r, e)?.get ? r[e] = n : r.$set({ [e]: n }));
			}
		});
	}), r.forEach((e) => {
		me(o.prototype, e, { get() {
			return this.$$c?.[e];
		} });
	}), a && (o = a(o)), e.element = o, o;
}
// TidalCard.svelte
var Na = /* @__PURE__ */ Oi("<div class=\"loading-state svelte-11pw7by\">Loading...</div>"), Pa = /* @__PURE__ */ Oi("<div class=\"redirect-copy-group svelte-11pw7by\"><input type=\"text\" class=\"input-field readonly text-wrap svelte-11pw7by\" readonly=\"\"/> <button class=\"btn-primary copy-btn svelte-11pw7by\">Copy</button></div> <p class=\"helper-text svelte-11pw7by\">This auto-generated URI must be registered in your Tidal Developer Applications.</p>", 1), Fa = /* @__PURE__ */ Oi("<button class=\"btn-ghost svelte-11pw7by\">+ Add Account</button>"), Ia = /* @__PURE__ */ Oi("<span class=\"status-badge success svelte-11pw7by\">✓ Authenticated</span>"), La = /* @__PURE__ */ Oi("<span class=\"status-badge warning svelte-11pw7by\">⚠ Not Authenticated</span>"), Ra = /* @__PURE__ */ Oi("<span class=\"status-badge active svelte-11pw7by\">● Active</span>"), za = /* @__PURE__ */ Oi("<div class=\"account-item svelte-11pw7by\"><div class=\"account-info svelte-11pw7by\"><div class=\"account-name svelte-11pw7by\"> </div> <div class=\"account-badges svelte-11pw7by\"><!> <!></div></div> <div class=\"account-actions svelte-11pw7by\"><button class=\"link-btn svelte-11pw7by\">⚙️ Edit</button> <button class=\"link-btn svelte-11pw7by\"> </button> <button> </button> <button class=\"btn-danger svelte-11pw7by\">✕</button></div></div>"), Ba = /* @__PURE__ */ Oi("<div class=\"empty-accounts svelte-11pw7by\">No accounts added yet. Click \"Add Account\" to get started.</div>"), Va = /* @__PURE__ */ Oi("<div class=\"settings-section svelte-11pw7by\"><div class=\"section-header svelte-11pw7by\"><h3 class=\"section-title svelte-11pw7by\">Global Redirect URI (Immutable)</h3> <button class=\"btn-ghost svelte-11pw7by\"> </button></div> <!></div> <div class=\"settings-section svelte-11pw7by\"><div class=\"section-header svelte-11pw7by\"><h3 class=\"section-title svelte-11pw7by\"> </h3> <!></div> <div class=\"accounts-list svelte-11pw7by\"></div></div>", 1), Ha = /* @__PURE__ */ Oi("<div class=\"modal-overlay svelte-11pw7by\"><div class=\"modal-content svelte-11pw7by\"><div class=\"modal-header svelte-11pw7by\"><h3 class=\"modal-title svelte-11pw7by\"> </h3> <button class=\"close-btn svelte-11pw7by\">✕</button></div> <div class=\"modal-body svelte-11pw7by\"><label class=\"form-field svelte-11pw7by\"><span class=\"field-label svelte-11pw7by\">Account Name</span> <input type=\"text\" placeholder=\"My Tidal Account\" class=\"input-field svelte-11pw7by\"/></label> <label class=\"form-field svelte-11pw7by\"><span class=\"field-label svelte-11pw7by\">Client ID</span> <input type=\"text\" placeholder=\"Enter Tidal Client ID\" class=\"input-field svelte-11pw7by\"/></label> <label class=\"form-field svelte-11pw7by\"><span class=\"field-label svelte-11pw7by\">Client Secret</span> <div class=\"password-wrapper svelte-11pw7by\"><input placeholder=\"Enter Tidal Client Secret\" class=\"input-field svelte-11pw7by\"/> <button type=\"button\" class=\"toggle-visibility svelte-11pw7by\"> </button></div></label></div> <div class=\"modal-footer svelte-11pw7by\"><button class=\"btn-ghost svelte-11pw7by\">Cancel</button> <button class=\"btn-primary svelte-11pw7by\"> </button></div></div></div>"), Ua = /* @__PURE__ */ Oi("<section class=\"plugin-card svelte-11pw7by\"><div class=\"card-header svelte-11pw7by\"><div class=\"header-left svelte-11pw7by\"><h2 class=\"card-title svelte-11pw7by\">Tidal</h2> <span class=\"type-badge svelte-11pw7by\">Streaming Service</span></div></div> <!></section> <!>", 1), Wa = {
	hash: "svelte-11pw7by",
	code: ".plugin-card.svelte-11pw7by {background:var(--bg-surface, #0f172a);backdrop-filter:blur(12px);border:1px solid var(--border-subtle, #1e293b);border-radius:var(--radius, 12px);padding:24px;margin-bottom:24px;color:var(--text-primary, #f8fafc);}.card-header.svelte-11pw7by {display:flex;justify-content:space-between;align-items:center;margin-bottom:24px;padding-bottom:16px;border-bottom:1px solid var(--border-subtle);}.header-left.svelte-11pw7by {display:flex;align-items:center;gap:12px;}.card-title.svelte-11pw7by {margin:0;font-size:20px;font-weight:700;}.type-badge.svelte-11pw7by {font-size:11px;padding:4px 8px;background:rgba(20, 184, 166, 0.15);color:var(--color-primary);border-radius:4px;font-weight:600;text-transform:uppercase;}.loading-state.svelte-11pw7by {padding:24px;text-align:center;color:var(--text-muted);}.settings-section.svelte-11pw7by {margin-bottom:24px;}.section-header.svelte-11pw7by {display:flex;justify-content:space-between;align-items:center;margin-bottom:16px;}.section-title.svelte-11pw7by {margin:0;font-size:16px;font-weight:600;color:var(--text-primary);}.input-field.svelte-11pw7by {width:100%;padding:10px 14px;background:var(--bg-surface-elevated);border:1px solid var(--border-subtle);border-radius:8px;color:var(--text-primary);font-size:14px;transition:all 0.2s;}.input-field.svelte-11pw7by:focus {outline:none;border-color:var(--color-primary);box-shadow:0 0 0 2px rgba(20, 184, 166, 0.1);}.input-field.readonly.svelte-11pw7by {opacity:0.6;cursor:not-allowed;}.helper-text.svelte-11pw7by {font-size:11px;color:var(--text-muted);margin-top:4px;}.redirect-copy-group.svelte-11pw7by {display:flex;gap:8px;align-items:stretch;}.redirect-copy-group.svelte-11pw7by .input-field:where(.svelte-11pw7by) {flex:1;font-family:monospace;overflow:hidden;text-overflow:ellipsis;}.text-wrap.svelte-11pw7by {word-break:break-all;white-space:normal;height:auto;min-height:40px;}.copy-btn.svelte-11pw7by {padding:0 16px;height:auto;white-space:nowrap;}.accounts-list.svelte-11pw7by {display:flex;flex-direction:column;gap:8px;}.account-item.svelte-11pw7by {display:flex;justify-content:space-between;align-items:center;padding:12px 16px;background:rgba(255,255,255,0.03);border:1px solid rgba(255,255,255,0.05);border-radius:8px;}.account-info.svelte-11pw7by {display:flex;flex-direction:column;gap:4px;}.account-name.svelte-11pw7by {font-weight:600;font-size:14px;}.account-badges.svelte-11pw7by {display:flex;gap:8px;}.status-badge.svelte-11pw7by {font-size:10px;padding:2px 6px;border-radius:4px;font-weight:700;}.status-badge.success.svelte-11pw7by {background:rgba(34, 197, 94, 0.15);color:#22c55e;}.status-badge.warning.svelte-11pw7by {background:rgba(234, 179, 8, 0.15);color:#eab308;}.status-badge.active.svelte-11pw7by {background:rgba(20, 184, 166, 0.15);color:var(--color-primary, #14b8a6);}.account-actions.svelte-11pw7by {display:flex;gap:12px;align-items:center;}.link-btn.svelte-11pw7by {background:none;border:none;color:var(--color-primary, #14b8a6);font-size:13px;font-weight:600;cursor:pointer;}.link-btn.svelte-11pw7by:hover {text-decoration:underline;}.btn-ghost.svelte-11pw7by {padding:8px 16px;background:rgba(255,255,255,0.05);border:1px solid rgba(255,255,255,0.1);color:var(--text-primary);border-radius:8px;font-size:13px;cursor:pointer;transition:all 0.2s;}.btn-ghost.svelte-11pw7by:hover {background:rgba(255,255,255,0.1);}.btn-primary.svelte-11pw7by {padding:10px 20px;background:var(--color-primary, #14b8a6);color:var(--bg-canvas, #000000);border:none;border-radius:8px;font-weight:600;cursor:pointer;transition:all 0.2s;}.btn-primary.svelte-11pw7by:hover {opacity:0.9;}.btn-danger.svelte-11pw7by {background:rgba(239, 68, 68, 0.15);color:var(--color-danger);border:none;padding:8px 12px;border-radius:6px;cursor:pointer;}.modal-overlay.svelte-11pw7by {position:fixed;inset:0;background:rgba(0,0,0,0.7);display:flex;align-items:center;justify-content:center;z-index:1000;backdrop-filter:blur(4px);}.modal-content.svelte-11pw7by {background:#0f1216;border:1px solid var(--border-subtle);border-radius:12px;width:100%;max-width:440px;box-shadow:0 24px 48px rgba(0,0,0,0.5);}.modal-header.svelte-11pw7by {padding:16px 20px;border-bottom:1px solid rgba(255,255,255,0.05);display:flex;justify-content:space-between;align-items:center;}.modal-title.svelte-11pw7by {margin:0;font-size:16px;font-weight:700;}.close-btn.svelte-11pw7by {background:none;border:none;color:var(--text-muted);font-size:20px;cursor:pointer;}.modal-body.svelte-11pw7by {padding:20px;display:flex;flex-direction:column;gap:16px;}.modal-footer.svelte-11pw7by {padding:16px 20px;border-top:1px solid rgba(255,255,255,0.05);display:flex;justify-content:flex-end;gap:12px;}.form-field.svelte-11pw7by {display:flex;flex-direction:column;gap:6px;}.field-label.svelte-11pw7by {font-size:13px;color:var(--text-muted);}.password-wrapper.svelte-11pw7by {position:relative;display:flex;align-items:center;}.toggle-visibility.svelte-11pw7by {position:absolute;right:12px;background:none;border:none;cursor:pointer;opacity:0.6;color:var(--text-primary);}.empty-accounts.svelte-11pw7by {text-align:center;padding:16px;color:var(--text-muted);font-size:13px;background:rgba(255,255,255,0.02);border-radius:8px;border:1px dashed rgba(255,255,255,0.1);}"
};
function Ga(e, t) {
	He(t, !1), sa(e, Wa);
	let n = Ea(t, "apiBase", 12, ""), r = /* @__PURE__ */ St([]), i = /* @__PURE__ */ St(""), a = /* @__PURE__ */ St(!1), o = /* @__PURE__ */ St(!0), s = /* @__PURE__ */ St(!1), c = /* @__PURE__ */ St("add"), l = /* @__PURE__ */ St({
		id: null,
		account_name: "",
		client_id: "",
		client_secret: ""
	}), u = /* @__PURE__ */ St(!1), d = /* @__PURE__ */ St(!1);
	Hi(async () => {
		await f(), P(a, !!Y(i)), P(o, !1);
	});
	async function f() {
		try {
			let e = await (await fetch(`${n()}/accounts`)).json();
			e && (P(r, e.accounts || []), P(i, e.redirect_uri || ""), P(a, !!Y(i)));
		} catch (e) {
			console.error("Failed to load Tidal accounts:", e);
		}
	}
	function p() {
		P(c, "add"), P(l, {
			id: null,
			account_name: "",
			client_id: "",
			client_secret: ""
		}), P(u, !0), P(d, !1), P(s, !0);
	}
	async function m(e) {
		P(c, "edit");
		try {
			let t = await (await fetch(`${n()}/${e.id}`)).json();
			t?.account && (P(l, {
				id: t.account.id,
				account_name: t.account.account_name,
				client_id: t.account.client_id || "",
				client_secret: t.account.client_secret || ""
			}), P(u, !1), P(d, !1), P(s, !0));
		} catch (e) {
			console.error("Failed to load account credentials:", e);
		}
	}
	function h() {
		P(s, !1), P(u, !1), P(d, !1), P(l, {
			id: null,
			account_name: "",
			client_id: "",
			client_secret: ""
		});
	}
	async function g() {
		if (!Y(l).account_name.trim() || !Y(l).client_id.trim()) console.error("Account name and Client ID are required");
		else if (!Y(l).client_secret.trim()) console.error("Client Secret is required");
		else try {
			let e = {
				account_name: Y(l).account_name,
				client_id: Y(l).client_id,
				client_secret: Y(l).client_secret
			};
			Y(c) === "add" ? await fetch(`${n()}/accounts`, {
				method: "POST",
				headers: { "Content-Type": "application/json" },
				body: JSON.stringify(e)
			}) : await fetch(`${n()}/${Y(l).id}`, {
				method: "PUT",
				headers: { "Content-Type": "application/json" },
				body: JSON.stringify(e)
			}), h(), await f();
		} catch (e) {
			console.error("Failed to save account:", e);
		}
	}
	async function _(e, t) {
		try {
			await fetch(`${n()}/${e}/activate`, {
				method: "PUT",
				headers: { "Content-Type": "application/json" },
				body: JSON.stringify({ is_active: !t })
			}), await f();
		} catch (e) {
			console.error("Failed to toggle account:", e);
		}
	}
	async function v(e, t) {
		if (confirm(`Delete account "${t}"?`)) try {
			await fetch(`${n()}/${e}`, { method: "DELETE" }), await f();
		} catch (e) {
			console.error("Failed to delete account:", e);
		}
	}
	async function y(e) {
		try {
			let t = (await (await fetch(`${n()}/auth?account_id=${e}`)).json())?.auth_url;
			t ? window.location.href = t : console.error("Failed to get Tidal auth URL");
		} catch (e) {
			console.error("Failed to start OAuth:", e);
		}
	}
	var b = {
		get apiBase() {
			return n();
		},
		set apiBase(e) {
			n(e), Gt();
		}
	};
	xa();
	var x = Ua(), S = Ir(x), C = Q(Z(S), 2), w = (e) => {
		ki(e, Na());
	}, ee = (e) => {
		var t = Va(), n = Ir(t), o = Z(n), s = Q(Z(o), 2), c = Lr(s, !0);
		A(o);
		var l = Q(o, 2), u = (e) => {
			var t = Pa(), n = Ir(t), r = Z(n);
			fa(r);
			var a = Q(r, 2);
			A(n), oe(2), _a(r, () => Y(i), (e) => P(i, e)), $("click", a, () => {
				navigator.clipboard.writeText(Y(i)), alert("Copied to clipboard!");
			}), ki(e, t);
		};
		Wi(l, (e) => {
			Y(a) || e(u);
		}), A(n);
		var d = Q(n, 2), f = Z(d), h = Z(f), g = Lr(h), b = Q(h, 2), x = (e) => {
			var t = Fa();
			$("click", t, p), ki(e, t);
		};
		Wi(b, (e) => {
			Y(r), X(() => Y(r).length < 25) && e(x);
		}), A(f);
		var S = Q(f, 2);
		ta(S, 5, () => Y(r), qi, (e, t) => {
			var n = za(), r = Z(n), i = Z(r), a = Lr(i, !0), o = Q(i, 2), s = Z(o), c = (e) => {
				ki(e, Ia());
			}, l = (e) => {
				ki(e, La());
			};
			Wi(s, (e) => {
				Y(t), X(() => Y(t).is_authenticated) ? e(c) : e(l, -1);
			});
			var u = Q(s, 2), d = (e) => {
				ki(e, Ra());
			};
			Wi(u, (e) => {
				Y(t), X(() => Y(t).is_active) && e(d);
			}), A(o), A(r);
			var f = Q(r, 2), p = Z(f), h = Q(p, 2), g = Lr(h, !0), b = Q(h, 2);
			let x;
			var S = Lr(b, !0), C = Q(b, 2);
			A(f), A(n), hn(() => {
				Pi(a, (Y(t), X(() => Y(t).display_name || Y(t).account_name))), Pi(g, (Y(t), X(() => Y(t).is_authenticated ? "Reauthenticate" : "Authenticate"))), x = ca(b, 1, "btn-ghost svelte-11pw7by", null, x, { active: Y(t).is_active }), Pi(S, (Y(t), X(() => Y(t).is_active ? "Deactivate" : "Activate")));
			}), $("click", p, () => m(Y(t))), $("click", h, () => y(Y(t).id)), $("click", b, () => _(Y(t).id, Y(t).is_active)), $("click", C, () => v(Y(t).id, Y(t).display_name || Y(t).account_name)), ki(e, n);
		}, (e) => {
			ki(e, Ba());
		}), A(S), A(d), hn(() => {
			Pi(c, Y(a) ? "Expand" : "Collapse"), Pi(g, `Accounts (${Y(r), X(() => Y(r).length) ?? ""}/25)`);
		}), $("click", s, () => P(a, !Y(a))), ki(e, t);
	};
	Wi(C, (e) => {
		Y(o) ? e(w) : e(ee, -1);
	}), A(S);
	var T = Q(S, 2), E = (e) => {
		var n = Ha(), r = Z(n), i = Z(r), a = Z(i), o = Lr(a, !0), s = Q(a, 2);
		A(i);
		var f = Q(i, 2), p = Z(f), m = Q(Z(p), 2);
		fa(m), A(p);
		var _ = Q(p, 2), v = Q(Z(_), 2);
		fa(v), A(_);
		var y = Q(_, 2), b = Q(Z(y), 2), x = Z(b);
		fa(x);
		var S = Q(x, 2), C = Lr(S, !0);
		A(b), A(y), A(f);
		var w = Q(f, 2), ee = Z(w), T = Q(ee, 2), E = Lr(T, !0);
		A(w), A(r), A(n), hn(() => {
			Pi(o, Y(c) === "add" ? "Add Tidal Account" : "Edit Tidal Account"), pa(x, "type", Y(d) ? "text" : "password"), Pi(C, Y(d) ? "🙈" : "👁️"), Pi(E, Y(c) === "add" ? "Add Account" : "Save Changes");
		}), $("click", s, h), _a(m, () => Y(l).account_name, (e) => Ct(l, Y(l).account_name = e)), _a(v, () => Y(l).client_id, (e) => Ct(l, Y(l).client_id = e)), _a(x, () => Y(l).client_secret, (e) => Ct(l, Y(l).client_secret = e)), $("input", x, () => P(u, !0)), $("click", S, () => P(d, !Y(d))), $("click", ee, h), $("click", T, g), $("click", r, ba(function(e) {
			Ca.call(this, t, e);
		})), $("click", n, h), ki(e, n);
	};
	return Wi(T, (e) => {
		Y(s) && e(E);
	}), ki(e, x), Ue(b);
}
customElements.define("tidal-dashboard-card", Ma(Ga, { apiBase: {} }, [], [], { mode: "open" }));
export { Ga as default };
